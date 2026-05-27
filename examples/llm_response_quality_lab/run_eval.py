import argparse
import csv
import json
import os
import subprocess
import urllib.request
import ssl
from collections import Counter
from pathlib import Path
import statistics

BASE_DIR = Path(__file__).resolve().parent

FAILURE_CATEGORIES = [
    'Incomplete Answer',
    'Hallucination',
    'Irrelevant Answer',
    'Missing Context',
    'Poor Formatting',
    'Incorrect Reasoning',
    'Other',
]


def load_questions(path):
    with open(path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        return [row for row in reader]


def load_prompt(path):
    return Path(path).read_text(encoding='utf-8')


def build_prompt(template, question):
    return template.replace('{question}', question.strip())


def call_openai(prompt, model):
    try:
        import openai
    except Exception:
        raise RuntimeError('openai package is not available')

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY is not set')
    openai.api_key = api_key
    resp = openai.ChatCompletion.create(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=600,
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


def call_ollama(prompt, model):
    # Try HTTP endpoint if provided via OLLAMA_URL
    ollama_url = os.getenv('OLLAMA_URL')
    if ollama_url:
        try:
            data = json.dumps({'model': model, 'prompt': prompt}).encode('utf-8')
            req = urllib.request.Request(ollama_url, data=data, headers={'Content-Type': 'application/json'})
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                raw = resp.read().decode('utf-8')
                try:
                    parsed = json.loads(raw)
                    for k in ('response', 'text', 'output'):
                        if k in parsed:
                            return parsed[k]
                    for v in parsed.values():
                        if isinstance(v, str):
                            return v
                except Exception:
                    return raw
        except Exception:
            pass

    # CLI fallback
    try:
        proc = subprocess.run(['ollama', 'run', model], input=prompt.encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=60)
        return proc.stdout.decode('utf-8').strip()
    except Exception as e:
        raise RuntimeError(f'Ollama invocation failed: {e}')


def call_provider(prompt, model, provider='ollama'):
    if provider == 'openai':
        return call_openai(prompt, model)
    elif provider == 'ollama':
        return call_ollama(prompt, model)
    else:
        return call_ollama(prompt, model)


def score_responses_with_model(baseline, improved, model_name, provider='ollama'):
    scoring_instructions = (
        "You are an evaluator. Rate each response on these metrics (integers 1-5): correctness, relevance, completeness, clarity, hallucination_risk. "
        "Then compute overall score as the mean of the five metrics for each response. Pick a winner (baseline/improved/tie), choose one failure_category if applicable, and give a one-line note. "
        "Return ONLY a JSON object with the keys: baseline_correctness, baseline_relevance, baseline_completeness, baseline_clarity, baseline_hallucination_risk, "
        "improved_correctness, improved_relevance, improved_completeness, improved_clarity, improved_hallucination_risk, baseline_score, improved_score, winner, failure_category, notes."
    )

    categories_text = '\n'.join(f'- {c}' for c in FAILURE_CATEGORIES)
    prompt = (
        f"{scoring_instructions}\n\nFailure categories:\n{categories_text}\n\n"
        f"Baseline response:\n{baseline}\n\nImproved response:\n{improved}\n\nRespond in JSON."
    )

    raw = call_provider(prompt, model_name, provider=provider)
    text = raw.strip()
    start = text.find('{')
    if start != -1:
        text = text[start:]
    try:
        data = json.loads(text)
        return data
    except Exception:
        return None


def validate_judge_output(data):
    if not isinstance(data, dict):
        return None
    metric_names = ['correctness', 'relevance', 'completeness', 'clarity', 'hallucination_risk']
    normalized = {}
    for prefix in ('baseline', 'improved'):
        vals = []
        for m in metric_names:
            key = f'{prefix}_{m}'
            v = data.get(key)
            if v is None:
                return None
            try:
                vi = int(v)
            except Exception:
                return None
            if vi < 1 or vi > 5:
                return None
            normalized[key] = vi
            vals.append(vi)
        score_key = f'{prefix}_score'
        mean_score = sum(vals) / len(vals)
        provided = data.get(score_key)
        if provided is None or provided == '':
            normalized[score_key] = round(mean_score, 2)
        else:
            try:
                prov = float(provided)
                if abs(prov - mean_score) > 0.25:
                    normalized[score_key] = round(mean_score, 2)
                else:
                    normalized[score_key] = round(prov, 2)
            except Exception:
                normalized[score_key] = round(mean_score, 2)
    winner = data.get('winner', '')
    normalized['winner'] = winner if winner in ('baseline', 'improved', 'tie') else 'tie'
    fc = data.get('failure_category') or ''
    normalized['failure_category'] = fc if fc in FAILURE_CATEGORIES else ('Other' if fc else '')
    normalized['notes'] = data.get('notes', '')
    return normalized


def write_results(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Wrote results to {path}')


def generate_summary(rows, output_path):
    # Compute averages for overall scores and per-metric
    def safe_get(r, k):
        v = r.get(k)
        return None if v in (None, '', 'None') else float(v)

    overall_b = [safe_get(r, 'baseline_score') for r in rows if safe_get(r, 'baseline_score') is not None]
    overall_i = [safe_get(r, 'improved_score') for r in rows if safe_get(r, 'improved_score') is not None]
    avg_b = statistics.mean(overall_b) if overall_b else None
    avg_i = statistics.mean(overall_i) if overall_i else None
    improvement = (avg_i - avg_b) if (avg_b is not None and avg_i is not None) else None

    metric_names = ['correctness', 'relevance', 'completeness', 'clarity', 'hallucination_risk']
    per_metric_avgs = {}
    for prefix in ('baseline', 'improved'):
        for m in metric_names:
            key = f'{prefix}_{m}'
            vals = [r.get(key) for r in rows if r.get(key) not in (None, '', 'None')]
            vals_i = [int(v) for v in vals]
            per_metric_avgs[key] = statistics.mean(vals_i) if vals_i else None

    failures = [r.get('failure_category') for r in rows if r.get('failure_category')]
    failure_counts = Counter(failures)
    top_failures = failure_counts.most_common(5)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# Evaluation Summary\n\n')
        if avg_b is not None:
            f.write(f'- Baseline prompt average score: {avg_b:.2f}/5\n')
        else:
            f.write('- Baseline prompt average score: N/A\n')
        if avg_i is not None:
            f.write(f'- Improved prompt average score: {avg_i:.2f}/5\n')
        else:
            f.write('- Improved prompt average score: N/A\n')
        if improvement is not None:
            f.write(f'- Improvement: {improvement:.2f}\n')
        f.write('\n')
        f.write('## Per-metric averages\n\n')
        for k, v in per_metric_avgs.items():
            if v is not None:
                f.write(f'- {k}: {v:.2f}\n')
            else:
                f.write(f'- {k}: N/A\n')
        f.write('\n')
        f.write('## Most common failure categories\n\n')
        if top_failures:
            for k, v in top_failures:
                f.write(f'- {k}: {v}\n')
        else:
            f.write('- None recorded\n')

    print(f'Wrote summary to {output_path}')


def main():
    parser = argparse.ArgumentParser(description='Run prompt quality evaluation for the response quality lab.')
    parser.add_argument('--mode', choices=['baseline', 'improved', 'compare'], default='compare')
    parser.add_argument('--model', default=os.getenv('OLLAMA_MODEL', 'llama2'))
    parser.add_argument('--provider', choices=['ollama', 'openai'], default=os.getenv('EVAL_PROVIDER', 'ollama'))
    parser.add_argument('--questions', default=BASE_DIR / 'benchmark_questions.csv')
    parser.add_argument('--baseline', default=BASE_DIR / 'baseline_prompt.txt')
    parser.add_argument('--improved', default=BASE_DIR / 'improved_prompt.txt')
    parser.add_argument('--output-dir', default=BASE_DIR)
    parser.add_argument('--auto-score', action='store_true', help='Use the LLM to automatically score responses (requires provider).')
    args = parser.parse_args()

    questions = load_questions(args.questions)
    baseline_prompt = load_prompt(args.baseline)
    improved_prompt = load_prompt(args.improved)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for row in questions:
        question_text = row.get('question', '')
        row_id = row.get('id', '')

        baseline_result = ''
        improved_result = ''

        if args.mode in ('baseline', 'compare'):
            baseline_result = build_prompt(baseline_prompt, question_text)
        if args.mode in ('improved', 'compare'):
            improved_result = build_prompt(improved_prompt, question_text)

        # Call provider to get real responses if possible
        if args.provider and args.provider in ('ollama', 'openai'):
            try:
                if args.mode in ('baseline', 'compare'):
                    baseline_result = call_provider(baseline_result, args.model, provider=args.provider)
                if args.mode in ('improved', 'compare'):
                    improved_result = call_provider(improved_result, args.model, provider=args.provider)
            except Exception as e:
                print('Model call failed:', e)

        record = {
            'id': row_id,
            'question': question_text,
            'baseline_response': baseline_result,
            'improved_response': improved_result,
        }

        # initialize metric fields
        metric_names = ['correctness', 'relevance', 'completeness', 'clarity', 'hallucination_risk']
        for prefix in ('baseline', 'improved'):
            for m in metric_names:
                record[f'{prefix}_{m}'] = ''
            record[f'{prefix}_score'] = ''

        record['winner'] = ''
        record['failure_category'] = ''
        record['notes'] = ''

        if args.auto_score:
            try:
                raw = score_responses_with_model(baseline_result, improved_result, args.model, provider=args.provider)
                validated = validate_judge_output(raw) if raw else None
                if validated:
                    for k, v in validated.items():
                        record[k] = v
                else:
                    print('Auto-score: judge output invalid or unparseable; skipping validation for this item.')
            except Exception as e:
                print('Auto-scoring failed:', e)

        rows.append(record)

    output_file = output_dir / 'outputs' / 'evaluation_results.csv'
    fieldnames = ['id', 'question', 'baseline_response', 'improved_response']
    for prefix in ('baseline', 'improved'):
        for m in ['correctness', 'relevance', 'completeness', 'clarity', 'hallucination_risk']:
            fieldnames.append(f'{prefix}_{m}')
        fieldnames.append(f'{prefix}_score')
    fieldnames += ['winner', 'failure_category', 'notes']

    write_results(output_file, rows, fieldnames)

    summary_file = output_dir / 'reports' / 'evaluation_summary.md'
    generate_summary(rows, summary_file)


if __name__ == '__main__':
    main()
import argparse
import csv
import os
import sys
from pathlib import Path

try:
    import openai
except ImportError:
    openai = None

BASE_DIR = Path(__file__).resolve().parent


def load_questions(path):
    with open(path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        return [row for row in reader]


def load_prompt(path):
    return Path(path).read_text(encoding='utf-8')


def build_prompt(template, question):
    return template.replace('{question}', question.strip())


def call_openai(prompt, model):
    if openai is None:
        import argparse
        import csv
        import json
        import os
        from collections import Counter
        from pathlib import Path
        import statistics
        import subprocess
        import urllib.request
        import urllib.parse
        import urllib.error
        import ssl

        try:
            import openai
        except ImportError:
            openai = None

        BASE_DIR = Path(__file__).resolve().parent

        FAILURE_CATEGORIES = [
            'Incomplete Answer',
            'Hallucination',
            'Irrelevant Answer',
            'Missing Context',
            'Poor Formatting',
            'Incorrect Reasoning',
            'Other',
        ]


        def load_questions(path):
            with open(path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                return [row for row in reader]


        def load_prompt(path):
            return Path(path).read_text(encoding='utf-8')


        def build_prompt(template, question):
            return template.replace('{question}', question.strip())


        def call_openai(prompt, model):
            if openai is None:
                raise RuntimeError('openai package is not installed.')

            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise RuntimeError('OPENAI_API_KEY is not set.')

            openai.api_key = api_key
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=600,
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()


        def call_ollama(prompt, model):
            """Call Ollama via HTTP (if OLLAMA_URL env set) or via CLI fallback.

            HTTP contract (best-effort): POST JSON {"model":..., "prompt":...} -> returns JSON with 'response' or plain text.
            CLI fallback: echo prompt | ollama run <model>
            """
            # Try HTTP endpoint if provided
            ollama_url = os.getenv('OLLAMA_URL')
            if ollama_url:
                try:
                    data = json.dumps({'model': model, 'prompt': prompt}).encode('utf-8')
                    req = urllib.request.Request(ollama_url, data=data, headers={'Content-Type': 'application/json'})
                    # ignore SSL issues for localhost scenarios
                    ctx = ssl.create_default_context()
                    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                        raw = resp.read().decode('utf-8')
                        try:
                            parsed = json.loads(raw)
                            # try common keys
                            for k in ('response', 'text', 'output'):
                                if k in parsed:
                                    return parsed[k]
                            # fallback to first string value
                            for v in parsed.values():
                                if isinstance(v, str):
                                    return v
                        except Exception:
                            return raw
                except Exception:
                    pass

            # CLI fallback: use `ollama run <model>` and pass prompt via stdin
            try:
                proc = subprocess.run(['ollama', 'run', model], input=prompt.encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=60)
                return proc.stdout.decode('utf-8').strip()
            except Exception as e:
                raise RuntimeError(f'Ollama call failed: {e}')


        def score_responses_with_model(baseline, improved, model_name, provider='openai'):
            """Ask the model to score both responses and return structured JSON."""
            scoring_instructions = (
                "You are an evaluator. Given a question's two responses, rate each response from 1 (poor) to 5 (excellent) "
                "on overall helpfulness, factuality, and relevance. Then select the winner ('baseline', 'improved', or 'tie'), "
                "pick a single failure category from the provided list if applicable, and provide a one-line note. "
                "Return ONLY a JSON object with keys: baseline_score (int), improved_score (int), winner (str), failure_category (str or null), notes (str)."
            )

            categories_text = '\n'.join(f'- {c}' for c in FAILURE_CATEGORIES)
            prompt = (
                f"{scoring_instructions}\n\nFailure categories:\n{categories_text}\n\n"\
                f"Baseline response:\n{baseline}\n\nImproved response:\n{improved}\n\nRespond in JSON."
            )

            try:
                if provider == 'openai':
                    raw = call_openai(prompt, model_name)
                elif provider == 'ollama':
                    raw = call_ollama(prompt, model_name)
                else:
                    raw = call_openai(prompt, model_name)
                # Try to extract JSON from the model output
                text = raw.strip()
                # find first '{'
                start = text.find('{')
                if start != -1:
                    text = text[start:]
                data = json.loads(text)
                return data
            except Exception:
                return None


        def write_results(path, rows, fieldnames):
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f'Wrote results to {path}')


        def generate_summary(rows, output_path):
            scores_b = [int(r['baseline_score']) for r in rows if r.get('baseline_score') not in (None, '', 'None')]
            scores_i = [int(r['improved_score']) for r in rows if r.get('improved_score') not in (None, '', 'None')]

            avg_b = statistics.mean(scores_b) if scores_b else None
            avg_i = statistics.mean(scores_i) if scores_i else None
            improvement = (avg_i - avg_b) if (avg_b is not None and avg_i is not None) else None

            failures = [r.get('failure_category') for r in rows if r.get('failure_category')]
            failure_counts = Counter(failures)
            top_failures = failure_counts.most_common(5)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('# Evaluation Summary\n\n')
                if avg_b is not None:
                    f.write(f'- Baseline prompt average score: {avg_b:.2f}/5\n')
                else:
                    f.write('- Baseline prompt average score: N/A\n')
                if avg_i is not None:
                    f.write(f'- Improved prompt average score: {avg_i:.2f}/5\n')
                else:
                    f.write('- Improved prompt average score: N/A\n')
                if improvement is not None:
                    f.write(f'- Improvement: {improvement:.2f}\n')
                f.write('\n')
                f.write('## Most common failure categories\n\n')
                if top_failures:
                    for k, v in top_failures:
                        f.write(f'- {k}: {v}\n')
                else:
                    f.write('- None recorded\n')

            print(f'Wrote summary to {output_path}')


        def main():
            parser = argparse.ArgumentParser(description='Run prompt quality evaluation for the response quality lab.')
            parser.add_argument('--mode', choices=['baseline', 'improved', 'compare'], default='compare')
            parser.add_argument('--model', default=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'))
            parser.add_argument('--questions', default=BASE_DIR / 'benchmark_questions.csv')
            parser.add_argument('--baseline', default=BASE_DIR / 'baseline_prompt.txt')
            parser.add_argument('--improved', default=BASE_DIR / 'improved_prompt.txt')
            parser.add_argument('--output-dir', default=BASE_DIR)
            parser.add_argument('--auto-score', action='store_true', help='Use the LLM to automatically score responses (requires API key).')
            args = parser.parse_args()

            questions = load_questions(args.questions)
            baseline_prompt = load_prompt(args.baseline)
            improved_prompt = load_prompt(args.improved)
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            if openai is None or not os.getenv('OPENAI_API_KEY'):
                print('NOTE: openai package or API key not available; model calls will be skipped.')

            rows = []
            for row in questions:
                question_text = row.get('question', '')
                row_id = row.get('id', '')

                baseline_result = ''
                improved_result = ''

                if args.mode in ('baseline', 'compare'):
                    baseline_result = build_prompt(baseline_prompt, question_text)
                if args.mode in ('improved', 'compare'):
                    improved_result = build_prompt(improved_prompt, question_text)

                # If API available, call the model to get actual answers
                if openai is not None and os.getenv('OPENAI_API_KEY'):
                    try:
                        if args.mode in ('baseline', 'compare'):
                            if args.provider == 'openai':
                                baseline_result = call_openai(baseline_result, args.model)
                            else:
                                baseline_result = call_ollama(baseline_result, args.model)
                        if args.mode in ('improved', 'compare'):
                            if args.provider == 'openai':
                                improved_result = call_openai(improved_result, args.model)
                            else:
                                improved_result = call_ollama(improved_result, args.model)
                    except Exception as e:
                        print('Model call failed:', e)

                record = {
                    'id': row_id,
                    'question': question_text,
                    'baseline_response': baseline_result,
                    'improved_response': improved_result,
                    'baseline_score': '',
                    'improved_score': '',
                    'winner': '',
                    'failure_category': '',
                    'notes': '',
                }

                # Optional automatic scoring via the model
                if args.auto_score:
                    try:
                        provider = args.provider
                        # auto-score requires a working provider endpoint (OpenAI or Ollama)
                        scores = score_responses_with_model(baseline_result, improved_result, args.model, provider=provider)
                        if scores:
                            record['baseline_score'] = scores.get('baseline_score', '')
                            record['improved_score'] = scores.get('improved_score', '')
                            record['winner'] = scores.get('winner', '')
                            record['failure_category'] = scores.get('failure_category', '')
                            record['notes'] = scores.get('notes', '')
                    except Exception:
                        pass

                rows.append(record)

            output_file = output_dir / 'outputs' / 'evaluation_results.csv'
            fieldnames = ['id', 'question', 'baseline_response', 'improved_response', 'baseline_score', 'improved_score', 'winner', 'failure_category', 'notes']
            write_results(output_file, rows, fieldnames)

            # Generate a human-friendly summary report
            summary_file = output_dir / 'reports' / 'evaluation_summary.md'
            generate_summary(rows, summary_file)

            if not (openai is not None and os.getenv('OPENAI_API_KEY')):
                print('Run again with --auto-score and OPENAI_API_KEY set to have the model score responses automatically.')


        if __name__ == '__main__':
            main()
