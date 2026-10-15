# Judge contract

The executable prompt is `JUDGE_PROMPT` in [contracts.py](../dilemma_bench/contracts.py). Each experiment snapshots its exact text. Judge records also save the complete messages used for grading.

The judge receives the case, rubric, and raw response. It receives no intervention prefix, model identity, condition label, or repeat index. Response content may still reveal those details.

The output has `criteria` and `commitments` objects. Each expected ID maps to a value, explanation, and exact evidence quotes. Local criteria use 0, 1, 2, or null. MoReBench criteria use true, false, or null to describe presence. Negative weights do not invert the judge's presence label. Commitment labels are descriptive and appear only for the local pilot rubric.

The parser checks IDs, types, explanations, and literal quotations. Malformed grades are missing evaluations, never zero scores. The checks do not prove that the judge's interpretation is correct.
