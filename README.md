# dilemma-bench

Measure how a model's written moral judgments change under controlled prompt interventions.

Run the same dilemmas with neutral wording, a user favoring either option, unrelated context, or instructions embedded in that context. Repeat each condition in independent conversations. A separate judge grades the responses without receiving the intervention prompt or model identity.

The runner supports the eight local pilot cases and the pinned public MoReBench dataset. It preserves MoReBench's expert rubric items. Our structured response format, batched grader, and descriptive reports are adaptations, not a reproduction of the paper's published scores.

## Run the offline demo

Python 3.11 or later is sufficient. There are no runtime dependencies. Run these commands from the repository root:

```sh
git clone https://github.com/0xKitsune/dilemma-bench.git
cd dilemma-bench
python3 -m unittest discover -s tests -v
python3 -m dilemma_bench demo --out runs/demo
```

Open `runs/demo/report.md`. The demo makes no network calls and labels every report as synthetic. Its deliberately programmed decision changes test the pipeline; they say nothing about a model's moral behavior. Choose a new output directory to repeat the demo.

## Run a model experiment

Follow the [runbook](docs/runbook.md) for credentials, exact model selection, importing MoReBench, call limits, resumption, and report interpretation.

```sh
python3 -m dilemma_bench prepare \
  --config configs/preference.json --out runs/preference-001 \
  --model "$RESPONDENT_MODEL" --judge-model "$JUDGE_MODEL"

python3 -m dilemma_bench respond runs/preference-001 --execute --max-calls 10
python3 -m dilemma_bench grade runs/preference-001 --execute --max-calls 10
python3 -m dilemma_bench report runs/preference-001
```

Preparation makes no model calls. Live execution uses `OPENROUTER_API_KEY` from the environment. Each execution command attempts at most ten calls by default. Rerun the same command to continue pending work. Inspect the frozen manifest before spending.

## Experiment definitions

| Config | Cases | Conditions | Repeats | Response calls | Maximum grade calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| `configs/preference.json` | 8 local | Baseline, prefer A, prefer B | 5 | 120 | 120 |
| `configs/context.json` | 8 local | Baseline, 2 context sizes, 4 poison conditions | 5 | 280 | 280 |
| `configs/morebench-context.json` | 4 public MoReBench cases | Baseline, 2 context sizes | 5 | 60 | 60 |

The public import has 500 theory-neutral cases. The four-case selection is a plumbing pilot, not a representative sample. MoReBench stores alternatives in prose; A/B experiments require reviewed option mappings. Context experiments work without those mappings, but cannot report A/B choice shifts.

Read the [experiment protocol](docs/evaluation.md), [research notes](docs/research.md), [draft axioms](docs/axioms.md), [architecture](docs/architecture.md), and [source attribution](docs/attribution.md).

Status: runnable experiment setup, verified with synthetic outputs and the real public dataset. No live model experiment or human validation of the judge has been performed. Named-framework trials and automatic significance testing are not implemented.
