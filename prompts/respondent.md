# Respondent contract

The executable prompt is `RESPONDENT_PROMPT` in [contracts.py](../dilemma_bench/contracts.py). Every experiment snapshots its exact text and rendered messages in `manifest.json`.

Responses contain four JSON string fields: `decision`, `justification`, `strongest_objection`, and `sensitivity`. Decisions use a, b, other, or refuse. Unmapped MoReBench cases use other and give a recommendation in prose. The prompt requests a public justification of roughly 150 to 250 words, not private reasoning.

A/B labels appear only when the dataset provides reviewed alternatives. The structured format is an adaptation and may itself influence model behavior.
