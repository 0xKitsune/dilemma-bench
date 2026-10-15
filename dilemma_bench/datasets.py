"""Dataset boundaries: local cases and a pinned MoReBench public release."""

import ast
import csv
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen

REVISION = "d900e89f942f784f8e0113935034b4f0541a0b55"
SOURCE = f"https://huggingface.co/datasets/morebench/morebench/resolve/{REVISION}/morebench_public.csv"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def import_morebench(output, mapping_path=None):
    output = Path(output)
    raw_path = output.with_suffix('.csv')
    if output.exists() or raw_path.exists():
        raise ValueError(f"Refusing to overwrite {output}")
    raw = urlopen(SOURCE, timeout=60).read()
    mappings = json.loads(Path(mapping_path).read_text()) if mapping_path else {}
    cases = []
    for index, row in enumerate(csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))):
        case_id = f"morebench-{index:04d}"
        criteria = ast.literal_eval(row["RUBRIC"])
        case = {
            "id": case_id,
            "scenario": row["DILEMMA"],
            "options": None,
            "rubric": [{"id": c["id"], "text": c["title"], "weight": c["weight"],
                        "dimension": c["annotations"]["rubric_dimension"]} for c in criteria],
            "metadata": {k: v for k, v in row.items() if k not in {"RUBRIC", "DILEMMA"}},
            "source_row": index,
        }
        if case_id in mappings:
            mapping = mappings[case_id]
            if mapping["scenario_sha256"] != hashlib.sha256(case["scenario"].encode()).hexdigest():
                raise ValueError(f"Option mapping refers to different scenario: {case_id}")
            if not mapping.get("reviewed_by"):
                raise ValueError(f"Option mapping needs reviewed_by: {case_id}")
            case["options"] = mapping["options"]
            case["option_mapping"] = mapping
        cases.append(case)
    if set(mappings) - {c["id"] for c in cases}:
        raise ValueError("Option mapping contains unknown case IDs")
    data = {"version": "morebench-public-" + REVISION, "source": SOURCE,
            "source_sha256": hashlib.sha256(raw).hexdigest(), "license": "CC-BY-4.0",
            "citation": "Chiu et al., MoReBench, https://arxiv.org/abs/2510.16380",
            "adaptation": "Converted CSV rubrics to JSON; optional reviewed choice labels added.",
            "cases": cases}
    validate_dataset(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return len(cases)


def validate_dataset(data):
    cases = data["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("Dataset must contain cases")
    ids = [c["id"] for c in cases]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Case IDs must be nonempty and unique")
    for case in cases:
        if not isinstance(case["scenario"], str) or not case["scenario"].strip():
            raise ValueError("A case needs a scenario")
        options = case.get("options")
        if options is not None and (not isinstance(options, dict) or set(options) != {"a", "b"} or
                                   any(not isinstance(v, str) or not v.strip() for v in options.values())):
            raise ValueError("Options must have nonempty a and b text")
        if "rubric" in case:
            rubric = case["rubric"]
            if not rubric or len({c["id"] for c in rubric}) != len(rubric):
                raise ValueError("Rubric IDs must be unique within a case")
            for c in rubric:
                if type(c["weight"]) is not int or c["weight"] not in {-3, -2, -1, 1, 2, 3}:
                    raise ValueError("MoReBench rubric weights must be nonzero integers from -3 to 3")
                if not c["text"] or not c["dimension"]:
                    raise ValueError("Rubric text and dimension are required")
        elif not case.get("case_checks"):
            raise ValueError("Local cases need case_checks")
    return data
