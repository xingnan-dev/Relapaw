import json
from pathlib import Path

from app.evaluation.recorded_outputs import PROVIDER_ERROR_CODES, main, run_recordings


DATASET = Path(__file__).parents[1] / "evals" / "recorded_outputs_v1.json"


def test_recorded_dataset_matches_expectations_without_network() -> None:
    report = run_recordings(DATASET)

    assert report["recorded_only"] is True
    assert report["network_calls"] == 0
    assert report["total_cases"] == 14
    assert report["expectation_matches"] == 14
    assert report["passed"] is True


def test_recorded_dataset_covers_every_stable_provider_error() -> None:
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    recorded_errors = {
        case["provider_error"]
        for group in dataset["groups"]
        for case in group["cases"]
        if "provider_error" in case
    }

    assert recorded_errors == PROVIDER_ERROR_CODES


def test_reports_keep_incompatible_versions_in_separate_groups() -> None:
    report = run_recordings(DATASET)

    assert len(report["groups"]) == 2
    assert {group["descriptor"]["model_provider"] for group in report["groups"]} == {
        "openai",
        "qwen",
    }
    assert all(group["expectation_match_rate"] == 1.0 for group in report["groups"])


def test_cli_returns_success_for_recorded_dataset(capsys) -> None:
    assert main([str(DATASET)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["dataset_version"] == "recorded-output-eval/v1"
