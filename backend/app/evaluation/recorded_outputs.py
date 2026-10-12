from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.evaluation.text_understanding import evaluate_payload
from app.schemas.analysis import AdapterDescriptor


PROVIDER_ERROR_CODES = {
    "MODEL_AUTHENTICATION_FAILED",
    "MODEL_PERMISSION_DENIED",
    "MODEL_TIMEOUT",
    "MODEL_RATE_LIMITED",
    "MODEL_NETWORK_ERROR",
    "MODEL_OUTPUT_INVALID",
    "MODEL_OUTPUT_INCOMPLETE",
    "MODEL_REFUSED",
    "MODEL_REQUEST_REJECTED",
    "MODEL_PROVIDER_UNAVAILABLE",
    "MODEL_PROVIDER_ERROR",
}

REVIEW_FIELDS = {
    "observation_interpretation_separated": "REVIEW_INTERPRETATION_BOUNDARY",
    "unsupported_assertions_absent": "REVIEW_UNSUPPORTED_ASSERTION",
    "confidence_calibrated": "REVIEW_CONFIDENCE_CALIBRATION",
}


def _group_key(descriptor: AdapterDescriptor) -> str:
    return "|".join(
        (
            descriptor.model_provider,
            descriptor.model_name,
            descriptor.model_version,
            descriptor.prompt_contract_version,
            descriptor.input_contract_version,
            descriptor.output_contract_version,
        )
    )


def run_recordings(path: str | Path) -> dict[str, Any]:
    recording_path = Path(path)
    dataset = json.loads(recording_path.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    group_counts: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"total": 0, "expectation_matches": 0}
    )

    for group in dataset["groups"]:
        descriptor = AdapterDescriptor.model_validate(group["descriptor"])
        group_key = _group_key(descriptor)
        for case in group["cases"]:
            actual_errors: set[str] = set()
            provider_error = case.get("provider_error")
            if provider_error is not None:
                if provider_error not in PROVIDER_ERROR_CODES:
                    actual_errors.add("UNKNOWN_PROVIDER_ERROR")
                else:
                    actual_errors.add(provider_error)
            else:
                actual_errors.update(
                    evaluate_payload(
                        case_id=case["id"],
                        input_data=case["input"],
                        candidate_output=case.get("recorded_output"),
                    )
                )
                review = case.get("human_review", {})
                for field, error_code in REVIEW_FIELDS.items():
                    if review.get(field) is False:
                        actual_errors.add(error_code)

            expected_errors = sorted(case.get("expected_error_codes", []))
            actual_errors_sorted = sorted(actual_errors)
            matched = actual_errors_sorted == expected_errors
            results.append(
                {
                    "case_id": case["id"],
                    "group_key": group_key,
                    "expected_error_codes": expected_errors,
                    "actual_error_codes": actual_errors_sorted,
                    "expectation_matched": matched,
                }
            )
            group_counts[group_key]["total"] += 1
            group_counts[group_key]["expectation_matches"] += int(matched)
            group_counts[group_key]["descriptor"] = descriptor.model_dump()

    groups = []
    for key, values in sorted(group_counts.items()):
        total = values["total"]
        groups.append(
            {
                "group_key": key,
                "descriptor": values["descriptor"],
                "total_cases": total,
                "expectation_matches": values["expectation_matches"],
                "expectation_match_rate": values["expectation_matches"] / total,
            }
        )

    matched_total = sum(result["expectation_matched"] for result in results)
    return {
        "dataset_version": dataset["version"],
        "dataset_path": str(recording_path),
        "recorded_only": True,
        "network_calls": 0,
        "total_cases": len(results),
        "expectation_matches": matched_total,
        "expectation_match_rate": matched_total / len(results) if results else 0.0,
        "passed": bool(results) and matched_total == len(results),
        "groups": groups,
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate recorded provider outputs")
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args(argv)
    report = run_recordings(args.dataset)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
