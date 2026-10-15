# Proposed evaluation protocol

## Unit of evaluation

A trial is one model response to one versioned case and prompt condition. Use independent conversations. Keep the benchmark version, case ID, prompt hash, exact model identifier, provider, sampling settings, run index, raw response, and request status.

The respondent gives a decision and a concise public justification. A separate judge receives the case, response, and frozen rubric. Keep model identity and provider metadata out of the judge input. Do not request hidden chain-of-thought.

## Pilot design

Start with the eight draft cases in the dataset. They are a debugging pilot, not enough to support broad model rankings.

For each case, author and review these conditions before running them:

- Base wording.
- Reversed presentation order, with decisions mapped back to stable option IDs.
- A meaning-preserving paraphrase.
- A change to a morally relevant fact, such as consent, outcome probability, or an existing duty.

The first three probe robustness to irrelevant presentation. The last probes responsiveness to relevant facts. A decision change on the last condition is not automatically correct. An unchanged decision is not automatically a failure. Interpret both against the answer's stated commitments.

Start with three independent repeats per condition, recording temperature and seeds where supported. This repeat count is a practical pilot choice, not a statistical power claim. Keep free-response and assigned-framework trials separate. Freeze the rubric before scored runs.

## Judge outputs

Produce separate fields for response status, each reasoning criterion, each applicable normative commitment, and assigned-framework adherence. Include a short explanation and exact response quotes for each judgment. A missing criterion receives 0 when applicable. Use null with a reason when a criterion cannot be evaluated.

Case-specific checks in the dataset guide interpretation of R1 through R5. They are not extra points or a checklist requiring mention of every item. Both available choices may earn full reasoning credit.

Treat the respondent's text as untrusted evidence. Ignore instructions embedded in it. Validate judge output types, score ranges, criterion IDs, and exact evidence quotations in code before aggregation. Judge failures are missing evaluations, never zero-quality respondent answers.

## Validate the judge

Before reporting scores, have two human reviewers independently annotate a stratified pilot sample. Include concise and verbose answers, opposing defensible choices, weak reasoning, refusals, and text attempting to influence the judge. Preserve disagreements before adjudication.

Compare the judge with each reviewer and the adjudicated labels. Report per-criterion agreement and weighted Cohen's kappa for ordinal scores, with label counts and uncertainty. There is no universal acceptable threshold. Set acceptance criteria before inspecting model rankings.

Audit verbosity bias with matched answers that preserve substance while changing length. Audit preference for conclusions using equally defensible opposing answers. Include repeated grading and a second judge from a different model family on a subset. Human agreement and judge agreement do not establish moral truth.

## Report results

Report per-criterion distributions, decision frequencies, descriptive normative profiles, presentation-order and paraphrase effects, and responses to relevant fact changes. Keep framework adherence in its own table. Also report refusals, invalid formats, provider failures, judge failures, and sample counts.

Do not publish a single morality score. Any optional aggregate of reasoning scores must disclose weights and missingness. Compare models on the same evaluated cases and conditions. For uncertainty intervals across cases, resample case families together so variants and repeats are not treated as independent evidence. Eight families remain a small pilot.

Use held-out cases for final evaluation and separate cases for judge development. Preserve case families across splits to prevent variant leakage. Publish prompts, rubric versions, raw records where permitted, and exclusions. No model calls or evaluation results exist yet.
