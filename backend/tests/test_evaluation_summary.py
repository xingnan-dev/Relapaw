import json
from pathlib import Path

from app.evaluation.summary_report import main, verify_summary


REPORT = Path(__file__).parents[1] / "evals" / "evaluation_summary_v1.json"


def test_frozen_summary_is_internally_consistent() -> None:
    result = verify_summary(REPORT)

    assert result["verified"] is True
    assert result["errors"] == []
    assert result["offline_cases"] == 9
    assert result["recorded_cases"] == 14
    assert result["live_runs"] == 3
    assert result["live_requests"] == 6


def test_summary_preserves_not_qualified_human_decision() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))

    assert report["qualification"]["status"] == "NOT_QUALIFIED"
    assert all(run["human_review"] == "failed" for run in report["live_provider_evaluation"]["runs"])
    assert all(run["retries"] == 0 for run in report["live_provider_evaluation"]["runs"])
    assert all(run["database_writes"] == 0 for run in report["live_provider_evaluation"]["runs"])


def test_reproduction_commands_cannot_trigger_live_requests() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    commands = report["reproduction"]["commands"]

    assert report["reproduction"]["network_required"] is False
    assert all("--execute" not in command for command in commands)


def test_summary_cli_returns_success(capsys) -> None:
    assert main([str(REPORT)]) == 0
    assert json.loads(capsys.readouterr().out)["verified"] is True
