# Experiment runner architecture

The public interface is `prepare`, `respond`, `grade`, and `report`. Importing MoReBench is an explicit network operation. `demo` exercises the full pipeline with synthetic fixtures and no network.

## Data and ownership

`datasets.py` owns external dataset parsing and provenance. `contracts.py` owns the response and judge contracts and runtime prompts. `experiment.py` owns prompt construction, immutable planning, API execution, and atomic record publication. `reporting.py` reads those artifacts and computes comparisons. `cli.py` parses commands.

The core records are JSON objects:

- A case has a stable ID, scenario, optional reviewed A/B options, and either local checks or imported rubric criteria.
- A trial has a case ID, condition ID, repeat index, exact messages, prompt hash, and deterministic ID.
- A manifest freezes the full selected case set, rubric snapshots, prompts, config, model IDs, mode, and shuffled trial list. A self-hash detects edits.
- An attempt records the request input before dispatch, then its provider response or failure. Completed outputs retain raw content, parsed fields when valid, completion status, and timing.

`prepare(config_path, directory, model, judge_model, mock)` creates a new experiment directory. `execute(directory, stage, max_calls, retry_errors, execute_live)` resumes one stage. `report(directory)` writes JSON and Markdown summaries without contacting a provider.

## Persistence and recovery

A run directory has `manifest.json`, `responses/`, `grades/`, `attempts/`, and reports. One process owns the writer lock. Records are written to a temporary file, flushed, and renamed into place. Results are tied to the manifest and trial; grades record a hash of the exact response record they evaluated.

Before each remote call, the runner writes a pending attempt. If the process dies after dispatch, the next invocation sees that unresolved attempt and skips it unless explicitly asked to retry errors. There is no claim of exactly-once execution across a remote API. A retry can incur duplicate cost.

Once a response is complete, invalid, or truncated, ordinary resume does not replace it. Error retries create another numbered attempt and update the latest stage record. New experiments use separate directories. Read reports after the writer finishes.

## Design choice

We compared per-trial JSON artifacts with a SQLite experiment store. The file design was selected for direct inspectability, a small standard-library installation, and explicit handling of ambiguous requests. The independent design review also favored the file design, particularly its retry policy. We retained the alternative design's requirements for reviewed option mappings and literal evidence checks.

We accepted a single writer and many small files instead of introducing database schema migrations. We kept provider adaptation inside the experiment coordinator rather than adding a separate wrapper layer. Signed MoReBench presence judgments and local ordinal scores remain distinct.

The design comparison used the available GPT model because the skill's preferred cross-family models were unavailable in this session. It is not evidence of cross-family review diversity.

## Extension boundaries

Add a new input-prefix intervention to the config validator and `condition_text`, then test that its messages differ in the intended place and that grader inputs remain unchanged. A custom text prefix needs no code change. Do not mutate a frozen plan.

Relevant-fact variants require a design that supplies the revised case to both respondent and grader. Assigned frameworks require versioned cards and dedicated rubric handling. Multi-turn conversations, retrieval poisoning, training-data poisoning, and automatic judge calibration are outside the current implementation.
