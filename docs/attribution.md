# Sources and attribution

MoReBench is the work of Yu Ying Chiu and collaborators. See [the paper and complete author list](https://arxiv.org/abs/2510.16380), [upstream code](https://github.com/morebench/morebench), and [dataset card](https://huggingface.co/datasets/morebench/morebench).

The importer uses public dataset revision `d900e89f942f784f8e0113935034b4f0541a0b55`. That dataset card declares [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). Imported scenarios and criteria retain that license. The import records attribution, source URL, revision, source-byte hash, and source row numbers. Keep that attribution and identify adaptations when redistributing imported data or results containing it.

The importer converts the public CSV's rubric representation to JSON and optionally adds reviewed choice labels. It preserves criterion text, identifiers, dimensions, and signed weights. The raw CSV is saved beside the JSON. Imported data and run outputs are excluded from Git by default.

This repository is an independent intervention experiment setup. It is not an official MoReBench release, and its reports are not directly comparable to the paper's scores. The upstream code is available under its own MIT license; this runner was implemented separately rather than vendoring that code.

The eight local pilot scenarios use wording written for this project around familiar philosophical dilemma structures. Their rubric is a proposal and has not undergone expert validation.
