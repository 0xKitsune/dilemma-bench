# Research precedents

There are established research methods for evaluating moral responses, but the sources below target different constructs. None establishes a universal moral correctness score.

| Precedent | What it measures | Use here |
| --- | --- | --- |
| [ETHICS](https://arxiv.org/abs/2008.02275) | Prediction of human moral judgments across commonsense morality, justice, duties, virtue, and utility | An external comparison for judgment prediction, separate from justification quality |
| [MoralChoice](https://www.cs.columbia.edu/~blei/papers/ScherrerShiFederBlei2023.pdf) | Moral choices and uncertainty under different question formulations | Repeated choices and robustness to wording |
| [MoReBench](https://arxiv.org/abs/2510.16380) | Procedural moral reasoning with expert-written, scenario-specific criteria. MoReBench-Theory separately tests assigned ethical frameworks | The closest precedent for the response-and-judge design |
| [MT-Bench judge study](https://arxiv.org/abs/2306.05685) | LLM judging and its position, verbosity, and self-enhancement biases | Validate the judge and audit its biases |

[Are LLMs Bad at Moral Reasoning?](https://arxiv.org/abs/2606.11635) challenges conclusions drawn from MoReBench by changing the elicitation task. This motivates checking whether a rubric measures defensible reasoning or merely coverage of its authors' preferred considerations.

Our current direction uses MoReBench as an evaluation resource for controlled prompt interventions. The local pilot also includes descriptive moral profiles. This combination is a design proposal, not a validated research standard. The sources do not validate our cases, criteria, weights, or judge prompts.

Review source dataset licenses and attribution requirements before importing examples. The local starter cases in this repository use newly written wording inspired by familiar dilemma structures. They are not copied benchmark rows. Public cases may already be familiar to models. New wording does not establish freedom from contamination.

The public importer and runtime are documented in the [runbook](runbook.md). The importer pins the public 500-case theory-neutral release; this differs from the paper's description of the full 1,000-scenario collection. Our structured output and grading protocol are adaptations, not a published-score reproduction.
