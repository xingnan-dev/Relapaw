import json
from pathlib import Path

from app.evaluation.text_understanding import evaluate_case, main, run_dataset


DATASET = Path(__file__).parents[1] / "evals" / "text_understanding_v1.json"


def test_bundled_dataset_matches_all_frozen_expectations() -> None:
    report = run_dataset(DATASET)

    assert report["offline"] is True
    assert report["total_cases"] == 9
    assert report["expectation_matches"] == 9
    assert report["expectation_match_rate"] == 1.0
    assert report["passed"] is True


def test_evaluator_detects_expectation_drift() -> None:
    case = json.loads(DATASET.read_text(encoding="utf-8"))["cases"][0]
    case["expected_pass"] = False
    case["expected_error_codes"] = ["EVIDENCE_INVALID"]

    result = evaluate_case(case)

    assert result.actual_pass is True
    assert result.expectation_matched is False


def test_cli_returns_success_for_frozen_dataset(capsys) -> None:
    assert main([str(DATASET)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["dataset_version"] == "text-understanding-eval/v1"
    assert report["passed"] is True


def test_owner_interpretation_cannot_support_a_claim_as_observed_fact() -> None:
    case = json.loads(DATASET.read_text(encoding="utf-8"))["cases"][0]
    case["input"]["evidence"].append(
        {
            "key": "interpretation:1:interpretation",
            "source_type": "OWNER_INTERPRETATION",
            "source_id": 1,
            "field_path": "interpretation",
            "observed_at": "2026-10-12T10:00:00Z",
            "recorded_at": "2026-10-12T10:01:00Z",
            "excerpt": "它可能还想在外面待一会儿",
        }
    )
    case["candidate_output"]["claims"][0]["evidence"] = [
        {"evidence_key": "interpretation:1:interpretation", "role": "SUPPORTS"}
    ]
    case["expected_pass"] = False
    case["expected_error_codes"] = ["INTERPRETATION_SUPPORT_INVALID"]

    result = evaluate_case(case)

    assert result.actual_error_codes == ["INTERPRETATION_SUPPORT_INVALID"]
    assert result.expectation_matched is True
