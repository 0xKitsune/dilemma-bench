"""Command-line entry points; live inference is always explicit."""

import argparse
from pathlib import Path
import sys

from .datasets import import_morebench
from .experiment import execute, prepare
from .reporting import report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Controlled moral-dilemma experiments')
    commands = parser.add_subparsers(dest='command', required=True)
    importer = commands.add_parser('import-morebench', help='Download the pinned public dataset')
    importer.add_argument('--out', default='data/morebench-public.json')
    importer.add_argument('--option-mappings', help='Reviewed case ID to options mapping JSON')
    plan = commands.add_parser('prepare', help='Freeze inputs without making model calls')
    plan.add_argument('--config', required=True)
    plan.add_argument('--out', required=True)
    plan.add_argument('--model')
    plan.add_argument('--judge-model')
    plan.add_argument('--mock', action='store_true')
    for name in ['respond', 'grade']:
        runner = commands.add_parser(name, help='Resume pending trials, at most max-calls requests')
        runner.add_argument('run')
        runner.add_argument('--max-calls', type=int, default=10)
        runner.add_argument('--execute', action='store_true', help='Permit billed calls for a live manifest')
        runner.add_argument('--retry-errors', action='store_true', help='Retry errors/pending calls; may duplicate spend after timeout')
    reporter = commands.add_parser('report', help='Write report.json and report.md; no network')
    reporter.add_argument('run')
    demo = commands.add_parser('demo', help='Run synthetic fixtures end to end, no network or key')
    demo.add_argument('--out', default='runs/demo')
    args = parser.parse_args(argv)
    try:
        if args.command == 'import-morebench':
            count = import_morebench(args.out, args.option_mappings)
            print(f'Imported {count} public cases into {args.out}')
        elif args.command == 'prepare':
            manifest = prepare(args.config, args.out, args.model, args.judge_model, args.mock)
            count = len(manifest['trials'])
            print(f"Prepared {count} responses and up to {count} grades in {args.out}; mode={manifest['mode']}")
            print('No model calls made. Inspect manifest.json before execution.')
        elif args.command in {'respond', 'grade'}:
            count = execute(args.run, 'responses' if args.command == 'respond' else 'grades',
                            args.max_calls, args.retry_errors, args.execute)
            print(f'Attempted {count} calls. Generate a report to inspect failures and remaining work.')
        elif args.command == 'report':
            report(args.run)
            print(f'Wrote {Path(args.run) / "report.md"} and report.json')
        else:
            manifest = prepare('configs/preference.json', args.out, mock=True)
            count = len(manifest['trials'])
            execute(args.out, 'responses', count)
            execute(args.out, 'grades', count)
            report(args.out)
            print(f'SYNTHETIC DEMO complete: {Path(args.out) / "report.md"}')
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0
