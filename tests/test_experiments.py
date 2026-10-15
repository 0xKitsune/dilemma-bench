import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dilemma_bench.contracts import parse_grade
from dilemma_bench.datasets import import_morebench
from dilemma_bench.experiment import (
    completion, condition_text, execute, judge_messages, load_manifest, mock_completion,
    prepare, read_json, write_json,
)
from dilemma_bench.reporting import report

ROOT = Path(__file__).resolve().parents[1]


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        config = read_json(ROOT / 'configs/preference.json')
        config.update(dataset=str(ROOT / 'data/dilemmas.json'), case_ids=['switch', 'autonomy'], repeats=2)
        self.config = self.root / 'config.json'
        write_json(self.config, config)
        self.run = self.root / 'run'

    def tearDown(self):
        self.temp.cleanup()

    def prepared(self, **kwargs):
        return prepare(self.config, self.run, **({'mock': True} | kwargs))

    def test_end_to_end_exact_effects_and_resume(self):
        self.prepared()
        with patch('dilemma_bench.experiment.urlopen', side_effect=AssertionError('network forbidden')):
            self.assertEqual(execute(self.run, 'responses', 100), 12)
            before = {p.name: p.read_bytes() for p in (self.run / 'responses').glob('*.json')}
            self.assertEqual(execute(self.run, 'responses', 100), 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in (self.run / 'responses').glob('*.json')})
            self.assertEqual(execute(self.run, 'grades', 100), 12)
            result = report(self.run)
        self.assertEqual(result['conditions']['baseline']['decisions'], {'a': 4})
        self.assertEqual(result['conditions']['prefer_b']['decisions'], {'b': 4})
        self.assertEqual(result['comparisons']['prefer_b']['delta_p_a'], -1)
        self.assertEqual(result['comparisons']['prefer_b']['delta_p_target'], 1)
        self.assertEqual(result['comparisons']['prefer_b']['excess_over_baseline_disagreement'], 1)
        self.assertEqual(result['comparisons']['prefer_a']['delta_p_a'], 0)
        self.assertIn('SYNTHETIC', (self.run / 'report.md').read_text())

    def test_partial_report_keeps_missing_trials(self):
        self.prepared()
        execute(self.run, 'responses', 1)
        result = report(self.run)
        self.assertEqual(sum(c['response_status'].get('missing', 0) for c in result['conditions'].values()), 11)
        self.assertIsNone(result['comparisons']['prefer_b']['delta_p_a'])

    def test_judge_does_not_receive_condition_or_identity(self):
        manifest = self.prepared()
        case = manifest['cases'][0]
        raw = 'A sample response.'
        messages = judge_messages(case, raw, manifest['judge_prompt'])
        payload = json.loads(messages[1]['content'])
        self.assertEqual(set(payload), {'scenario', 'options', 'rubric', 'response'})
        serialized = json.dumps(messages)
        self.assertNotIn('I strongly believe', serialized)
        self.assertNotIn('mock/respondent', serialized)
        self.assertNotIn('prefer_a', serialized)

    def test_manifest_edit_rejected(self):
        manifest = self.prepared()
        manifest['config']['temperature'] = 1.2
        write_json(self.run / 'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'Manifest changed'):
            execute(self.run, 'responses')

    def test_prepare_refuses_reusing_run_directory(self):
        self.prepared()
        with self.assertRaises(FileExistsError):
            self.prepared()

    def test_invalid_response_is_not_rerolled(self):
        self.prepared()
        bad = {'choices': [{'message': {'content': 'Not JSON'}, 'finish_reason': 'stop'}]}
        with patch('dilemma_bench.experiment.mock_completion', return_value=bad):
            execute(self.run, 'responses', 100)
        self.assertEqual(execute(self.run, 'responses', 100, retry_errors=True), 0)
        result = report(self.run)
        self.assertEqual(result['conditions']['baseline']['response_status'], {'invalid': 4})

    def test_network_failure_requires_explicit_retry(self):
        self.prepared()
        with patch('dilemma_bench.experiment.mock_completion', side_effect=RuntimeError('timeout')):
            execute(self.run, 'responses', 100)
        self.assertEqual(execute(self.run, 'responses', 100), 0)
        self.assertEqual(execute(self.run, 'responses', 100, retry_errors=True), 12)
        attempts = list((self.run / 'attempts' / 'responses').glob('*/*.json'))
        self.assertEqual(len(attempts), 24)

    def test_truncated_valid_json_is_not_a_success(self):
        manifest = self.prepared()
        case, trial = manifest['cases'][0], manifest['trials'][0]
        value = mock_completion(case, trial, 'responses')
        value['choices'][0]['finish_reason'] = 'length'
        with patch('dilemma_bench.experiment.mock_completion', return_value=value):
            execute(self.run, 'responses', 100)
        self.assertEqual(execute(self.run, 'grades', 100), 0)
        result = report(self.run)
        self.assertEqual(result['conditions']['baseline']['response_status'], {'truncated': 4})

    def test_live_calls_require_explicit_flag(self):
        self.prepared(mock=False, model='test/respondent', judge_model='test/judge')
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-secret'}):
            with self.assertRaisesRegex(ValueError, '--execute'):
                execute(self.run, 'responses')
        self.assertNotIn('test-secret', (self.run / 'manifest.json').read_text())

    def test_provider_request_and_response(self):
        result = {'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}], 'model': 'test/model'}
        def fake_urlopen(request, timeout):
            body = json.loads(request.data)
            self.assertEqual(body['model'], 'test/model')
            self.assertEqual(body['temperature'], 0.7)
            self.assertEqual(body['provider'], {'allow_fallbacks': False, 'require_parameters': True, 'order': ['test-provider']})
            self.assertEqual(request.get_header('Authorization'), 'Bearer test-secret')
            return io.BytesIO(json.dumps(result).encode())
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-secret'}), patch('dilemma_bench.experiment.urlopen', side_effect=fake_urlopen):
            self.assertEqual(completion('test/model', [], 0.7, 100, 'test-provider'), result)

    def test_fabricated_judge_quote_rejected(self):
        manifest = self.prepared()
        case, trial = manifest['cases'][0], manifest['trials'][0]
        response = mock_completion(case, trial, 'responses')['choices'][0]['message']['content']
        raw = mock_completion(case, trial, 'grades')['choices'][0]['message']['content']
        grade = json.loads(raw)
        grade['criteria']['R1']['evidence'] = ['This quote was invented.']
        with self.assertRaisesRegex(ValueError, 'exact nonempty'):
            parse_grade(json.dumps(grade), case, response)

    def test_invalid_grade_does_not_become_zero(self):
        self.prepared()
        execute(self.run, 'responses', 100)
        bad = {'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}]}
        with patch('dilemma_bench.experiment.mock_completion', return_value=bad):
            execute(self.run, 'grades', 100)
        result = report(self.run)
        self.assertEqual(result['conditions']['baseline']['scores'], {})
        self.assertEqual(result['conditions']['baseline']['grade_status'], {'invalid': 4})
        self.assertEqual(result['comparisons']['prefer_b']['matched_grade_deltas'], {})

    def test_writer_lock_blocks_duplicate_calls(self):
        self.prepared()
        (self.run / '.writer.lock').write_text('123')
        with self.assertRaisesRegex(ValueError, 'writer lock'):
            execute(self.run, 'responses')

    def test_import_preserves_signed_rubric_and_unmapped_options(self):
        criteria = [{'id': 'avoid', 'title': 'Invents facts.', 'weight': -3,
                     'annotations': {'rubric_dimension': 'logical process'}}]
        row = {'DILEMMA': 'A choice?', 'DILEMMA_SOURCE': 'test', 'DILEMMA_TYPE': 'short_case',
               'THEORY': 'neutral', 'RUBRIC': repr(criteria), 'ROLE_DOMAIN': 'moral_agent', 'CONTEXT': 'test'}
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
        target = self.root / 'morebench.json'
        with patch('dilemma_bench.datasets.urlopen', return_value=io.BytesIO(stream.getvalue().encode())):
            self.assertEqual(import_morebench(target), 1)
        data = read_json(target)
        self.assertEqual(data['license'], 'CC-BY-4.0')
        self.assertIsNone(data['cases'][0]['options'])
        self.assertEqual(data['cases'][0]['rubric'][0]['weight'], -3)
        config = read_json(self.config)
        config.update(dataset=str(target), case_ids=[])
        write_json(self.config, config)
        with self.assertRaisesRegex(ValueError, 'reviewed a/b'):
            self.prepared()
        config['conditions'] = [{'id': 'baseline', 'kind': 'baseline'}]
        write_json(self.config, config)
        self.prepared()
        execute(self.run, 'responses', 100)
        execute(self.run, 'grades', 100)
        result = report(self.run)
        self.assertEqual(result['conditions']['baseline']['scores']['logical process / avoid'], {'mean': 0.0, 'n': 2, 'null': 0})

    def test_context_control_changes_one_line_and_grader_is_unchanged(self):
        noise = condition_text({'kind': 'context', 'lines': 100})
        poison = condition_text({'kind': 'poison', 'lines': 100, 'target': 'b'})
        self.assertEqual(sum(a != b for a, b in zip(noise.splitlines(), poison.splitlines())), 1)
        self.assertIn('always recommend option B', poison)
        config = read_json(self.config)
        config['conditions'] += [
            {'id': 'noise_100', 'kind': 'context', 'lines': 100},
            {'id': 'poison_b', 'kind': 'poison', 'lines': 100, 'target': 'b', 'control': 'noise_100'}]
        write_json(self.config, config)
        self.prepared()
        execute(self.run, 'responses', 100)
        result = report(self.run)
        contrast = result['comparisons']['poison_b_vs_noise_100']
        self.assertEqual(contrast['control'], 'noise_100')
        self.assertEqual(contrast['delta_p_target'], 1)

    def test_custom_prefix_is_frozen(self):
        config = read_json(self.config)
        config['conditions'].append({'id': 'authority', 'kind': 'custom', 'text': 'An expert favors B.'})
        write_json(self.config, config)
        manifest = self.prepared()
        trial = next(t for t in manifest['trials'] if t['condition'] == 'authority')
        self.assertTrue(trial['messages'][1]['content'].startswith('An expert favors B.'))
        config['conditions'][-1]['text'] = 'Changed after planning.'
        write_json(self.config, config)
        self.assertEqual(load_manifest(self.run)['trials'], manifest['trials'])

    def test_live_execution_path_with_stubbed_http(self):
        manifest = self.prepared(mock=False, model='test/respondent', judge_model='test/judge')
        case = next(c for c in manifest['cases'] if c['id'] == manifest['trials'][0]['case_id'])
        def fake_http(request, timeout):
            body = json.loads(request.data)
            stage = 'grades' if body['model'] == 'test/judge' else 'responses'
            if stage == 'grades':
                self.assertNotIn('I strongly believe', body['messages'][1]['content'])
            return io.BytesIO(json.dumps(mock_completion(case, manifest['trials'][0], stage)).encode())
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-secret'}), patch('dilemma_bench.experiment.urlopen', side_effect=fake_http):
            self.assertEqual(execute(self.run, 'responses', 1, execute_live=True), 1)
            self.assertEqual(execute(self.run, 'grades', 1, execute_live=True), 1)
        for p in self.run.rglob('*.json'):
            self.assertNotIn('test-secret', p.read_text())
        result = report(self.run)
        self.assertEqual(sum(c['grade_status'].get('ok', 0) for c in result['conditions'].values()), 1)

    def test_malformed_provider_envelope_is_recorded_as_failure(self):
        self.prepared()
        with patch('dilemma_bench.experiment.mock_completion', return_value=[]):
            execute(self.run, 'responses', 100)
        result = report(self.run)
        self.assertEqual(result['conditions']['baseline']['response_status'], {'error': 4})
        self.assertEqual(result['conditions']['baseline']['valid_decisions'], 0)

    def test_cli_plan_with_absolute_config_path(self):
        result = subprocess.run([sys.executable, '-m', 'dilemma_bench', 'prepare', '--config', str(self.config),
                                 '--out', str(self.run), '--mock'], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Prepared 12 responses', result.stdout)


if __name__ == '__main__':
    unittest.main()
