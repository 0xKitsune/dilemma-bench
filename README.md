# dilemma-bench

A proposed benchmark for written responses to moral dilemmas, with a separate model evaluating the answers.

The benchmark separates reasoning quality, expressed moral commitments, and adherence to an assigned moral framework. Agreement with a framework does not increase the reasoning-quality score.

Status: research and protocol draft. The starter cases and prompts are proposals for discussion. No inference runner, validated judge, or model results exist yet.

- [Research precedents](docs/research.md)
- [Evaluation protocol](docs/evaluation.md)
- [Proposed axioms and rubrics](docs/axioms.md)
- [Starter dilemmas](data/dilemmas.json)
- [Respondent prompt](prompts/respondent.md)
- [Judge prompt](prompts/judge.md)

The first implementation should collect independent responses, grade each with a frozen rubric, and retain the raw records. Revise prompts between benchmark versions, never silently during a scored run. Evaluate public written justifications, which need not reveal the model's actual decision process.
