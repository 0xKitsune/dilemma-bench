"""Descriptive, case-balanced intervention comparisons with explicit missingness."""

from collections import Counter, defaultdict
from pathlib import Path
import random
import statistics

from .datasets import digest
from .experiment import load_manifest, read_json, write_json


def mean(values):
    return statistics.mean(values) if values else None


def interval(values):
    if len(values) < 2:
        return None
    rng = random.Random(731)
    samples = sorted(mean(rng.choices(values, k=len(values))) for _ in range(2000))
    return [samples[49], samples[1949]]


def read_record(directory, stage, trial, manifest):
    path = directory / stage / (trial['id'] + '.json')
    if not path.exists():
        return {'status': 'missing'}
    record = read_json(path)
    if record['trial_id'] != trial['id'] or record['manifest_sha256'] != manifest['manifest_sha256']:
        raise ValueError('Result belongs to a different trial or manifest')
    if stage == 'responses' and record['prompt_sha256'] != trial['prompt_sha256']:
        raise ValueError('Result prompt does not match planned prompt')
    return record


def report(directory):
    directory = Path(directory)
    manifest = load_manifest(directory)
    cases = {c['id']: c for c in manifest['cases']}
    grouped = defaultdict(list)
    for trial in manifest['trials']:
        response = read_record(directory, 'responses', trial, manifest)
        grade = read_record(directory, 'grades', trial, manifest)
        if grade['status'] != 'missing' and grade.get('response_sha256') != digest(response):
            raise ValueError('Grade refers to a different response record')
        grouped[trial['condition']].append((trial, response, grade))
    summary = {'mode': manifest['mode'], 'manifest_sha256': manifest['manifest_sha256'],
               'model': manifest['model'], 'judge_model': manifest['judge_model'],
               'conditions': {}, 'comparisons': {},
               'notes': ['Synthetic fixture output, not model evidence.' if manifest['mode'] == 'mock'
                         else 'Exploratory results; judge validity must be checked against human annotations.',
                         'Intervals resample case-level means, not independent variants or repetitions.',
                         'Decision comparisons require all repeats valid in both arms for each included case.',
                         'Refuse and other remain decision outcomes, not silently dropped answers.',
                         'MoReBench presence is criterion coverage, not an official benchmark score.']}
    for condition, rows in grouped.items():
        decisions, scores, commitments = Counter(), defaultdict(list), defaultdict(Counter)
        null_scores = Counter()
        statuses, grade_statuses, lengths = Counter(), Counter(), []
        costs, tokens, usage_count = [], [], 0
        by_case = defaultdict(list)
        for trial, response, grade in rows:
            statuses[response['status']] += 1
            grade_statuses[grade['status']] += 1
            if response.get('raw'):
                lengths.append(len(response['raw']))
            if response['status'] == 'ok':
                decision = response['parsed']['decision']
                decisions[decision] += 1
                by_case[trial['case_id']].append(decision)
            for record in [response, grade]:
                provider_response = record.get('provider_response')
                usage = provider_response.get('usage', {}) if isinstance(provider_response, dict) else {}
                if not isinstance(usage, dict):
                    usage = {}
                if usage:
                    usage_count += 1
                if isinstance(usage.get('cost'), (int, float)):
                    costs.append(usage['cost'])
                if isinstance(usage.get('total_tokens'), int):
                    tokens.append(usage['total_tokens'])
            if grade['status'] == 'ok':
                case = cases[trial['case_id']]
                rubric = {c['id']: c for c in case.get('rubric', [])}
                for key, entry in grade['parsed']['criteria'].items():
                    value = entry['value']
                    bucket = rubric[key]['dimension'] + (' / avoid' if rubric[key]['weight'] < 0 else ' / include') if rubric else key
                    if value is None:
                        null_scores[bucket] += 1
                    else:
                        scores[bucket].append(float(not value) if rubric and rubric[key]['weight'] < 0 else value)
                for key, entry in grade['parsed']['commitments'].items():
                    commitments[key][entry['value']] += 1
        disagreements = []
        for cid, labels in by_case.items():
            if not cases[cid].get('options'):
                continue
            n = len(labels)
            if n >= 2:
                counts = Counter(labels)
                disagreements.append(1 - sum(k * (k - 1) for k in counts.values()) / (n * (n - 1)))
        summary['conditions'][condition] = {
            'planned': len(rows), 'response_status': dict(statuses), 'grade_status': dict(grade_statuses),
            'decisions': dict(decisions), 'valid_decisions': sum(decisions.values()),
            'mean_response_characters': mean(lengths),
            'scores': {k: {'mean': mean(scores[k]), 'n': len(scores[k]), 'null': null_scores[k]}
                       for k in sorted(set(scores) | set(null_scores))},
            'commitments': {k: dict(v) for k, v in commitments.items()},
            'within_condition_disagreement': mean(disagreements),
            'recorded_cost_latest_attempts': sum(costs) if costs else None,
            'recorded_total_tokens_latest_attempts': sum(tokens) if tokens else None,
            'records_with_usage': usage_count,
        }
    contrasts = [(c['id'], 'baseline') for c in manifest['config']['conditions'] if c['id'] != 'baseline']
    contrasts += [(c['id'], c['control']) for c in manifest['config']['conditions']
                  if c.get('control', 'baseline') != 'baseline']
    for condition, control in contrasts:
        baseline_rows = grouped[control]
        rows = grouped[condition]
        contrast_name = condition if control == 'baseline' else condition + '_vs_' + control
        deltas_a, tvs, cross_disagreements, excess_disagreements = [], [], [], []
        target_deltas, included = [], []
        condition_spec = next(c for c in manifest['config']['conditions'] if c['id'] == condition)
        for cid, case in cases.items():
            if not case.get('options'):
                continue
            arms = [[r for t, r, _ in arm if t['case_id'] == cid] for arm in [baseline_rows, rows]]
            if any(len(arm) != manifest['config']['repeats'] or any(r['status'] != 'ok' for r in arm) for arm in arms):
                continue
            counts = [Counter(r['parsed']['decision'] for r in arm) for arm in arms]
            n = manifest['config']['repeats']
            probabilities = [{label: c[label] / n for label in ['a', 'b', 'other', 'refuse']} for c in counts]
            base, changed = probabilities
            included.append(cid)
            deltas_a.append(changed['a'] - base['a'])
            tvs.append(sum(abs(changed[k] - base[k]) for k in base) / 2)
            cross = 1 - sum(base[k] * changed[k] for k in base)
            cross_disagreements.append(cross)
            if n > 1:
                natural = 1 - sum(k * (k - 1) for k in counts[0].values()) / (n * (n - 1))
                excess_disagreements.append(cross - natural)
            if 'target' in condition_spec:
                target = condition_spec['target']
                target_deltas.append(changed[target] - base[target])
        score_deltas = defaultdict(list)
        base_index = {(t['case_id'], t['repeat']): g for t, _, g in baseline_rows}
        per_case = defaultdict(lambda: defaultdict(list))
        for trial, _, grade in rows:
            base_grade = base_index[(trial['case_id'], trial['repeat'])]
            if grade['status'] != 'ok' or base_grade['status'] != 'ok':
                continue
            case = cases[trial['case_id']]
            rubric = {c['id']: c for c in case.get('rubric', [])}
            for key, entry in grade['parsed']['criteria'].items():
                before = base_grade['parsed']['criteria'][key]['value']
                after = entry['value']
                if before is None or after is None:
                    continue
                bucket = rubric[key]['dimension'] + (' / avoid' if rubric[key]['weight'] < 0 else ' / include') if rubric else key
                delta = int(after) - int(before)
                if rubric and rubric[key]['weight'] < 0:
                    delta = -delta
                per_case[bucket][trial['case_id']].append(delta)
        for bucket, case_values in per_case.items():
            score_deltas[bucket] = [mean(v) for v in case_values.values()]
        summary['comparisons'][contrast_name] = {
            'condition': condition, 'control': control,
            'complete_mapped_cases': included, 'excluded_or_unmapped_cases': len(cases) - len(included),
            'delta_p_a': mean(deltas_a), 'delta_p_a_case_bootstrap_95': interval(deltas_a),
            'delta_p_target': mean(target_deltas), 'delta_p_target_case_bootstrap_95': interval(target_deltas),
            'empirical_total_variation': mean(tvs),
            'cross_condition_disagreement': mean(cross_disagreements),
            'excess_over_baseline_disagreement': mean(excess_disagreements),
            'matched_grade_deltas': {k: {'mean': mean(v), 'case_bootstrap_95': interval(v), 'cases': len(v)}
                                     for k, v in score_deltas.items()},
        }
    write_json(directory / 'report.json', summary)
    def fmt(value):
        return 'n/a' if value is None else f'{value:.3f}'
    lines = ['# Experiment report', '',
             '**SYNTHETIC DEMO. These are fixture outputs, not model results.**' if manifest['mode'] == 'mock'
             else '**Exploratory run. Review missingness and validate the judge before interpreting scores.**', '',
             f"Respondent: `{manifest['model']}`. Judge: `{manifest['judge_model']}`.", '',
             '| Condition | Planned | Valid decisions | Decisions | Response states | Grade states |',
             '| --- | ---: | ---: | --- | --- | --- |']
    for condition in [c['id'] for c in manifest['config']['conditions']]:
        item = summary['conditions'][condition]
        lines.append(f"| {condition} | {item['planned']} | {item['valid_decisions']} | {item['decisions']} | {item['response_status']} | {item['grade_status']} |")
    lines += ['', '## Changes relative to baseline or a named control', '',
              '| Condition | Complete mapped cases | Change in P(A) | Change in P(target) | Excess disagreement |',
              '| --- | ---: | ---: | ---: | ---: |']
    for condition, item in summary['comparisons'].items():
        lines.append(f"| {condition} | {len(item['complete_mapped_cases'])} | {fmt(item['delta_p_a'])} | {fmt(item['delta_p_target'])} | {fmt(item['excess_over_baseline_disagreement'])} |")
    lines += ['', 'The JSON report contains criterion and dimension summaries, commitment labels, matched grade changes, and case-bootstrap intervals.', '',
              'Missing and invalid grades never count as zero. Grade deltas use available case/repeat/criterion matches; decision comparisons require complete arms.', '',
              'For unmapped MoReBench cases, A/B decision shifts are unavailable. Inspect written recommendations or add reviewed mappings.', '',
              'Empirical distribution differences are noisy with few repeats. Bootstrap intervals cover the sampled cases, not all moral dilemmas.', '',
              'Usage totals include the latest attempt only. Inspect attempts/ for retry costs. Recorded provider costs may be absent.', '']
    (directory / 'report.md').write_text('\n'.join(lines))
    return summary
