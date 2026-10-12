from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.domain.enums import SafetyStatus
from app.schemas.analysis import UnderstandingInput, UnderstandingOutput


ERROR_SAFETY_OUTPUT_PRESENT = "SAFETY_OUTPUT_PRESENT"
ERROR_OUTPUT_MISSING = "OUTPUT_MISSING"
ERROR_CONTRACT_INVALID = "CONTRACT_INVALID"
ERROR_EVIDENCE_INVALID = "EVIDENCE_INVALID"
ERROR_PROHIBITED_CONTENT = "PROHIBITED_CONTENT"
ERROR_LANGUAGE_MISMATCH = "LANGUAGE_MISMATCH"

_CJK = re.compile(r"[\u3400-\u9fff]")
_PROHIBITED = re.compile(
    r"(?:\bdiagnos(?:e|ed|is)\b|\btreat(?:ment|ing)?\b|\bmedicat(?:e|ion)\b|"
    r"\bdosage\b|\b\d+(?:\.\d+)?\s*mg\b|诊断为|确诊|治疗方案|用药|剂量|毫克)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    expected_pass: bool
    actual_pass: bool
    expected_error_codes: list[str]
    actual_error_codes: list[str]
    expectation_matched: bool


def evaluate_case(case: dict[str, Any]) -> CaseResult:
    case_id = str(case["id"])
    expected_pass = bool(case["expected_pass"])
    expected_errors = sorted(str(code) for code in case.get("expected_error_codes", []))

    try:
        input_data = UnderstandingInput.model_validate(case["input"])
    except ValidationError:
        actual_errors = [ERROR_CONTRACT_INVALID]
        return _result(case_id, expected_pass, expected_errors, actual_errors)

    candidate = case.get("candidate_output")
    if input_data.safety_status != SafetyStatus.NORMAL:
        actual_errors = [] if candidate is None else [ERROR_SAFETY_OUTPUT_PRESENT]
        return _result(case_id, expected_pass, expected_errors, actual_errors)

    if candidate is None:
        return _result(case_id, expected_pass, expected_errors, [ERROR_OUTPUT_MISSING])

    try:
        output = UnderstandingOutput.model_validate(candidate)
    except ValidationError:
        return _result(case_id, expected_pass, expected_errors, [ERROR_CONTRACT_INVALID])

    errors: set[str] = set()
    allowed_evidence = {item.key for item in input_data.evidence}
    referenced_evidence = {
        reference.evidence_key
        for claim in output.claims
        for reference in claim.evidence
    }
    if not referenced_evidence.issubset(allowed_evidence):
        errors.add(ERROR_EVIDENCE_INVALID)

    generated_text = " ".join(
        [claim.statement for claim in output.claims]
        + [
            uncertainty.description
            for claim in output.claims
            for uncertainty in claim.uncertainties
        ]
    )
    if _PROHIBITED.search(generated_text):
        errors.add(ERROR_PROHIBITED_CONTENT)

    if _CJK.search(input_data.raw_owner_input) and generated_text and not _CJK.search(generated_text):
        errors.add(ERROR_LANGUAGE_MISMATCH)

    return _result(case_id, expected_pass, expected_errors, sorted(errors))


def _result(
    case_id: str,
    expected_pass: bool,
    expected_errors: list[str],
    actual_errors: list[str],
) -> CaseResult:
    actual_errors = sorted(actual_errors)
    actual_pass = not actual_errors
    return CaseResult(
        case_id=case_id,
        expected_pass=expected_pass,
        actual_pass=actual_pass,
        expected_error_codes=expected_errors,
        actual_error_codes=actual_errors,
        expectation_matched=(
            actual_pass == expected_pass and actual_errors == expected_errors
        ),
    )


def run_dataset(path: str | Path) -> dict[str, Any]:
    dataset_path = Path(path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    results = [evaluate_case(case) for case in dataset["cases"]]
    matched = sum(result.expectation_matched for result in results)
    total = len(results)
    return {
        "dataset_version": dataset["version"],
        "dataset_path": str(dataset_path),
        "offline": True,
        "total_cases": total,
        "expectation_matches": matched,
        "expectation_match_rate": matched / total if total else 0.0,
        "passed": matched == total and total > 0,
        "results": [asdict(result) for result in results],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run offline text-understanding evaluation")
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args(argv)
    report = run_dataset(args.dataset)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
