from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


QUALIFICATIONS = {"QUALIFIED", "NOT_QUALIFIED"}


def verify_summary(path: str | Path) -> dict[str, Any]:
    report_path = Path(path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    if report.get("version") != "evaluation-summary/v1":
        errors.append("SUMMARY_VERSION_INVALID")
    qualification = report.get("qualification", {}).get("status")
    if qualification not in QUALIFICATIONS:
        errors.append("QUALIFICATION_INVALID")

    offline = report.get("offline_evaluation", {})
    if offline.get("expectation_matches") != offline.get("total_cases"):
        errors.append("OFFLINE_EXPECTATIONS_INCOMPLETE")
    recorded = report.get("recorded_output_evaluation", {})
    if recorded.get("expectation_matches") != recorded.get("total_cases"):
        errors.append("RECORDED_EXPECTATIONS_INCOMPLETE")

    runs = report.get("live_provider_evaluation", {}).get("runs", [])
    if len({run.get("run_id") for run in runs}) != len(runs):
        errors.append("LIVE_RUN_ID_DUPLICATE")
    for run in runs:
        if run.get("requests_sent", 0) > run.get("budget", {}).get("max_requests", 0):
            errors.append("LIVE_REQUEST_BUDGET_EXCEEDED")
        if run.get("retries") != 0:
            errors.append("LIVE_RETRY_POLICY_VIOLATED")
        if run.get("database_writes") != 0:
            errors.append("LIVE_DATABASE_WRITE_VIOLATED")

    if qualification == "QUALIFIED" and any(
        run.get("human_review") != "passed" for run in runs
    ):
        errors.append("QUALIFICATION_CONTRADICTS_HUMAN_REVIEW")
    if qualification == "NOT_QUALIFIED" and not any(
        run.get("human_review") == "failed" for run in runs
    ):
        errors.append("NOT_QUALIFIED_WITHOUT_FAILED_REVIEW")

    commands = report.get("reproduction", {}).get("commands", [])
    if not commands or any("--execute" in command for command in commands):
        errors.append("REPRODUCTION_MUST_BE_OFFLINE_ONLY")

    return {
        "report_path": str(report_path),
        "report_version": report.get("version"),
        "verified": not errors,
        "errors": sorted(set(errors)),
        "qualification": report.get("qualification"),
        "offline_cases": offline.get("total_cases", 0),
        "recorded_cases": recorded.get("total_cases", 0),
        "live_runs": len(runs),
        "live_requests": sum(run.get("requests_sent", 0) for run in runs),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the frozen Evaluation summary")
    parser.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    result = verify_summary(args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
