# Run an intervention experiment

Run commands from the repository root with Python 3.11 or later. The runner uses the standard library. Optional installation with `python3 -m pip install -e .` provides the `dilemma-bench` command.

## 1. Verify the setup offline

```sh
python3 -m unittest discover -s tests -v
python3 -m dilemma_bench demo --out runs/demo
```

Inspect `runs/demo/report.md` and `report.json`. The demo runs 120 synthetic responses and 120 synthetic grades. The fixture always favors A at baseline and B in the prefer-B arm, so the reported prefer-B change in P(A) must be -1. These are test values, not research findings.

## 2. Select a dataset

For the local pilot, use `configs/preference.json` without downloading anything.

For the public MoReBench cases:

```sh
python3 -m dilemma_bench import-morebench
```

This downloads a pinned revision, saves the raw CSV and converted JSON under `data/`, and records its revision, source URL, SHA-256, attribution, rubric weights, and source rows. Imported files are ignored by Git. The importer refuses to overwrite existing outputs. Use `--out` with another filename for a fresh import.

Use `configs/morebench-context.json` for a four-case smoke experiment. Edit a copy of that config to select other case IDs or set `case_ids` to an empty list for all imported cases. Config dataset paths resolve relative to the config file, not the shell's directory.

For A/B preference or poisoning conditions, label the alternatives before creating the run. Make a mapping JSON keyed by case ID, with this structure:

```json
{
  "morebench-0000": {
    "scenario_sha256": "SHA256_OF_THE_EXACT_SCENARIO_UTF8_BYTES",
    "reviewed_by": "NAME_OF_REVIEWER",
    "options": {
      "a": "Accurate description of the first reviewed alternative",
      "b": "Accurate description of the second reviewed alternative"
    }
  }
}
```

Review labels against the complete source scenario. Preserve uncertainty and avoid adding facts. Compute the hash using `hashlib.sha256(scenario.encode()).hexdigest()` from the imported JSON's `scenario` string. Then import with `--option-mappings path/to/mappings.json --out data/morebench-mapped.json`. Select only mapped cases for an A/B experiment. The importer checks the scenario hash and reviewer field but cannot verify the quality of that human review.

## 3. Choose models and a call budget

Use exact OpenRouter model IDs supported by your account. Choose a judge from another model family when practical and later check a subset with another judge. Read [OpenRouter's request reference](https://openrouter.ai/docs/api/reference/overview) for supported parameters.

Set these environment variables locally:

```sh
export RESPONDENT_MODEL='replace-with-provider/model-id'
export JUDGE_MODEL='replace-with-provider/model-id'
```

Set `OPENROUTER_API_KEY` through your shell or secret manager. The program reads the environment directly and does not automatically load `.env`. Never put a key in a config, command argument, or tracked file.

The provider must support JSON-object output, temperature, and the configured output token limit. The runner requires parameter support and disables provider fallbacks. Optional `provider` and `judge_provider` config fields pin an OpenRouter provider slug. Without these, routing can still vary between requests. Inspect returned model and provider metadata in the records.

Estimate cost using the selected models' current prices and the full prompt sizes. A call cap limits requests, not dollars. Long context and rubric grading can dominate cost. Requested `max_tokens` may also constrain a model's reasoning budget. The runner does not configure provider-specific reasoning effort.

## 4. Freeze and inspect the plan

```sh
python3 -m dilemma_bench prepare \
  --config configs/preference.json \
  --out runs/preference-001 \
  --model "$RESPONDENT_MODEL" \
  --judge-model "$JUDGE_MODEL"
```

Inspect `runs/preference-001/manifest.json`. It contains the selected cases, provenance, rubric snapshots, exact respondent messages, judge instructions, model IDs, settings, repeat indices, and shuffled trial order. Preparation creates a new directory and does not call a model.

The local preference matrix has 8 cases × 3 conditions × 5 repeats = 120 responses and up to 120 grades. Each grade evaluates one response's rubric items together. This differs from upstream criterion-by-criterion judging.

Use a new run directory when changing any input. The runner rejects an edited manifest. Keep the same runner checkout while completing a run. The manifest records the runner version and Git commit, but does not archive the source checkout or establish that it was clean.

## 5. Run the first batch

```sh
python3 -m dilemma_bench respond runs/preference-001 --execute --max-calls 10
python3 -m dilemma_bench grade runs/preference-001 --execute --max-calls 10
python3 -m dilemma_bench report runs/preference-001
```

Inspect raw responses and grades. Check whether the chosen models honor the output format and whether outputs truncate. The report shows missing, error, invalid, and truncated records separately. A syntactically invalid response can still receive a reasoning grade; it cannot supply a valid structured decision. Truncated responses are excluded from grading.

If settings need adjustment, make a new pilot run. Do not selectively reroll inconvenient answers in a scored run.

## 6. Complete or resume

```sh
python3 -m dilemma_bench respond runs/preference-001 --execute --max-calls 120
python3 -m dilemma_bench grade runs/preference-001 --execute --max-calls 120
python3 -m dilemma_bench report runs/preference-001
```

Already completed, invalid, and truncated outputs are skipped. The call cap applies to new attempts in this invocation. Failed or interrupted requests are skipped unless you add `--retry-errors`.

A timeout or interruption may occur after the provider has billed a request. Retrying can charge again. Every attempt has its own record under `attempts/`; the stage directory holds the latest attempt. Do not use retrying as a way to select preferred decisions.

A writer lock prevents two execution commands from working on the same run concurrently. After a process crash, check the PID in `.writer.lock` and confirm no writer is active before removing that stale lock. Then review pending attempts before deciding whether to retry them. Reports should be generated after the writer stops.

## 7. Interpret and validate

Open `report.md` for the overview and `report.json` for measurements, denominators, and intervals. Read the [protocol](evaluation.md) before drawing conclusions. A missing metric is not a zero effect.

Compare judge labels with independent human annotations before publishing substantive findings. Include answers from all conditions, especially refusals, opposing defensible decisions, and responses containing injected instructions. The runner checks output shape and quotations, not moral soundness or resistance to all prompt injection.

Keep failed records and raw artifacts. `runs/` is ignored by Git; publish reviewed results intentionally. Recorded usage totals cover latest attempts only, so use `attempts/` and provider billing for total spend.
