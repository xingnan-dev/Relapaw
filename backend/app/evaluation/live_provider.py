from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from app.domain.enums import SafetyStatus
from app.evaluation.text_understanding import evaluate_payload
from app.schemas.analysis import UnderstandingInput

if TYPE_CHECKING:
    from app.services.understanding_adapter import TextUnderstandingAdapter


AUTH_ENV = "RELAPAW_LIVE_EVAL_AUTHORIZED"


def _build_capped_adapter(budget: dict[str, Any]) -> "TextUnderstandingAdapter":
    from app.core.config import settings
    from app.services.understanding_adapter import (
        OpenAIResponsesAdapter,
        QwenChatCompletionsAdapter,
    )

    api_key = settings.openai_api_key
    model = settings.openai_model.strip() if settings.openai_model else ""
    if api_key is None or not api_key.get_secret_value().strip() or not model:
        raise RuntimeError("Live evaluation provider is not configured")
    adapter_class = (
        QwenChatCompletionsAdapter
        if settings.model_provider.strip().lower() == "qwen"
        else OpenAIResponsesAdapter
    )
    return adapter_class(
        api_key=api_key.get_secret_value(),
        model=model,
        timeout_seconds=min(
            float(settings.openai_timeout_seconds), float(budget["timeout_seconds"])
        ),
        max_output_tokens=min(
            int(settings.openai_max_output_tokens), int(budget["max_output_tokens_per_request"])
        ),
        base_url=settings.openai_base_url.strip() if settings.openai_base_url else None,
        model_provider=settings.model_provider.strip() or "openai",
    )


def run_live_dataset(
    path: str | Path,
    *,
    execute: bool = False,
    authorized: bool = False,
    adapter: "TextUnderstandingAdapter | None" = None,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    dataset_path = Path(path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    budget = dataset["budget"]
    cases = dataset["cases"]
    if len(cases) > int(budget["max_requests"]):
        raise ValueError("Dataset exceeds frozen max_requests budget")

    plan = {
        "dataset_version": dataset["version"],
        "dataset_path": str(dataset_path),
        "mode": "execute" if execute else "dry-run",
        "authorized": authorized,
        "budget": budget,
        "planned_requests": len(cases),
        "database_writes": 0,
        "retries": 0,
    }
    if not execute:
        return {**plan, "ready_for_explicit_authorization": True, "requests_sent": 0}
    if not authorized:
        raise PermissionError("Live evaluation requires explicit authorization")

    from app.services.understanding_adapter import AdapterError

    selected_adapter = adapter or _build_capped_adapter(budget)
    results: list[dict[str, Any]] = []
    for case in cases:
        payload = UnderstandingInput.model_validate(case["input"])
        if payload.safety_status != SafetyStatus.NORMAL:
            results.append(
                {
                    "case_id": case["id"],
                    "latency_ms": 0,
                    "error_codes": ["ANALYSIS_BLOCKED_BY_SAFETY"],
                    "recorded_output": None,
                }
            )
            continue
        started = clock()
        try:
            output = selected_adapter.analyze(payload)
            elapsed_ms = round((clock() - started) * 1000, 3)
            output_data = output.model_dump(mode="json")
            errors = evaluate_payload(
                case_id=case["id"],
                input_data=case["input"],
                candidate_output=output_data,
            )
            results.append(
                {
                    "case_id": case["id"],
                    "latency_ms": elapsed_ms,
                    "error_codes": errors,
                    "recorded_output": output_data,
                }
            )
        except AdapterError as exc:
            elapsed_ms = round((clock() - started) * 1000, 3)
            results.append(
                {
                    "case_id": case["id"],
                    "latency_ms": elapsed_ms,
                    "error_codes": [exc.code],
                    "recorded_output": None,
                }
            )

    hard_gate_passed = all(not result["error_codes"] for result in results)
    return {
        **plan,
        "adapter_descriptor": selected_adapter.descriptor.model_dump(),
        "requests_sent": sum(
            1 for result in results if result["error_codes"] != ["ANALYSIS_BLOCKED_BY_SAFETY"]
        ),
        "execution_completed": True,
        "hard_gate_passed": hard_gate_passed,
        "human_review_required": True,
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Budgeted live Provider evaluation")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    authorized = os.getenv(AUTH_ENV) == "YES"
    try:
        report = run_live_dataset(
            args.dataset,
            execute=args.execute,
            authorized=authorized,
        )
    except (PermissionError, RuntimeError, ValueError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.execute:
        return 0
    return 0 if report["hard_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
