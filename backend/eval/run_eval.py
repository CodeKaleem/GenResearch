"""Run deterministic scoring for a serialized ProposalOutput fixture."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from models.schemas import ProposalOutput
from eval.scorers import numeric_accuracy, quality_report, section_coverage


def run_fixture(output_path: str | Path, gold_path: str | Path) -> dict:
    output = ProposalOutput.model_validate_json(Path(output_path).read_text())
    gold = json.loads(Path(gold_path).read_text())
    report = quality_report(output, gold.get("required_topics", []))
    report["numeric_accuracy"] = numeric_accuracy(output, gold.get("expected_numbers", []))
    report["section_coverage"] = section_coverage(output, gold.get("required_topics", []))
    return report


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m eval.run_eval OUTPUT.json GOLD.json")
    print(json.dumps(run_fixture(sys.argv[1], sys.argv[2]), indent=2))