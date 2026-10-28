from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from app.domain.enums import SafetyStatus
from app.schemas.analysis import UnderstandingInput
from app.schemas.assistant import AssistantGuidanceInput

if TYPE_CHECKING:
    from app.services.assistant_adapter import AssistantGuidanceAdapter
    from app.services.understanding_adapter import TextUnderstandingAdapter


AUTH_ENV = "RELAPAW_LIVE_QUALIFICATION_AUTHORIZED"


def _build_capped_adapters(
    budget: dict[str, Any],
) -> tuple["TextUnderstandingAdapter", "AssistantGuidanceAdapter"]:
    from app.core.config import settings
    from app.domain.qualification_endpoint import QWEN_BEIJING_ENDPOINT_POLICY, endpoint_matches_policy
    from app.services.assistant_adapter import QwenAssistantGuidanceAdapter
    from app.services.understanding_adapter import QwenChatCompletionsAdapter

    api_key = settings.openai_api_key
    model = settings.openai_model.strip() if settings.openai_model else ""
    base_url = settings.openai_base_url.strip() if settings.openai_base_url else ""
    if api_key is None or not api_key.get_secret_value().strip() or not model or not base_url:
        raise RuntimeError("Live qualification provider is not configured")
    if settings.model_provider.strip().lower() != "qwen":
        raise RuntimeError("Live qualification is frozen for the selected Qwen provider")
    if not endpoint_matches_policy(base_url, QWEN_BEIJING_ENDPOINT_POLICY):
        raise RuntimeError("Live qualification endpoint must match the frozen Qwen Beijing policy")
    common = {
        "api_key": api_key.get_secret_value(),
        "model": model,
        "timeout_seconds": min(float(settings.openai_timeout_seconds), float(budget["timeout_seconds"])),
        "max_output_tokens": min(
            int(settings.openai_max_output_tokens), int(budget["max_output_tokens_per_request"])
        ),
        "base_url": base_url,
        "model_provider": "qwen",
    }
    return QwenChatCompletionsAdapter(**common), QwenAssistantGuidanceAdapter(**common)


def _assert_frozen_subject(dataset: dict[str, Any], understanding: Any, guidance: Any) -> None:
    expected = dataset["qualification_subject"]
    descriptors = []
    if dataset.get("understanding_cases"):
        descriptors.append(understanding.descriptor)
    if dataset.get("guidance_cases"):
        descriptors.append(guidance.descriptor)
    if any(item.model_provider != expected["provider"] for item in descriptors):
        raise ValueError("Adapter provider does not match the frozen qualification subject")
    if any(item.model_name != expected["model"] for item in descriptors):
        raise ValueError("Adapter model does not match the frozen qualification subject")
    contracts = {item.prompt_contract_version for item in descriptors}
    if contracts != set(expected["prompt_contracts"]):
        raise ValueError("Adapter contracts do not match the frozen qualification subject")


def run_live_qualification(
    path: str | Path,
    *,
    execute: bool = False,
    authorized: bool = False,
    understanding_adapter: "TextUnderstandingAdapter | None" = None,
    guidance_adapter: "AssistantGuidanceAdapter | None" = None,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    dataset_path = Path(path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    budget = dataset["budget"]
    understanding_cases = dataset.get("understanding_cases", [])
    guidance_cases = dataset.get("guidance_cases", [])
    planned_requests = sum(
        1 for case in understanding_cases if case["input"]["safety_status"] == SafetyStatus.NORMAL
    ) + sum(
        1 for case in guidance_cases if case["input"]["current_record"]["safety_status"] == "NORMAL"
    )
    if planned_requests > int(budget["max_requests"]):
        raise ValueError("Dataset exceeds frozen max_requests budget")

    plan = {
        "dataset_version": dataset["version"],
        "dataset_path": str(dataset_path),
        "qualification_subject": dataset["qualification_subject"],
        "mode": "execute" if execute else "dry-run",
        "authorized": authorized,
        "budget": budget,
        "planned_requests": planned_requests,
        "database_writes": 0,
        "retries": 0,
    }
    if not execute:
        return {**plan, "ready_for_explicit_authorization": True, "requests_sent": 0}
    if not authorized:
        raise PermissionError("Live qualification requires explicit authorization")

    from app.schemas.assistant import AssistantGuidanceOutput
    from app.services.assistant_guidance import GuidanceExecutionError, _validate_output
    from app.services.understanding import AnalysisExecutionError, _validated_extraction_items
    from app.services.understanding_adapter import AdapterError

    if understanding_adapter is None or guidance_adapter is None:
        understanding_adapter, guidance_adapter = _build_capped_adapters(budget)
    _assert_frozen_subject(dataset, understanding_adapter, guidance_adapter)

    results: list[dict[str, Any]] = []
    for case in understanding_cases:
        payload = UnderstandingInput.model_validate(case["input"])
        if payload.safety_status != SafetyStatus.NORMAL:
            results.append({
                "case_id": case["id"], "contract": "text-understanding/v7",
                "latency_ms": 0, "error_codes": ["ANALYSIS_BLOCKED_BY_SAFETY"],
                "recorded_output": None,
            })
            continue
        started = clock()
        try:
            output = understanding_adapter.analyze(payload)
            try:
                _validated_extraction_items(payload, output)
                errors = []
            except AnalysisExecutionError as exc:
                errors = [exc.code]
            results.append({
                "case_id": case["id"], "contract": "text-understanding/v7",
                "latency_ms": round((clock() - started) * 1000, 3),
                "error_codes": errors, "recorded_output": output.model_dump(mode="json"),
            })
        except AdapterError as exc:
            results.append({
                "case_id": case["id"], "contract": "text-understanding/v7",
                "latency_ms": round((clock() - started) * 1000, 3),
                "error_codes": [exc.code], "recorded_output": None,
            })

    for case in guidance_cases:
        payload = AssistantGuidanceInput.model_validate(case["input"])
        if payload.current_record.safety_status != "NORMAL":
            results.append({
                "case_id": case["id"], "contract": guidance_adapter.descriptor.prompt_contract_version,
                "latency_ms": 0, "error_codes": ["ANALYSIS_BLOCKED_BY_SAFETY"],
                "recorded_output": None,
            })
            continue
        started = clock()
        try:
            output = AssistantGuidanceOutput.model_validate(guidance_adapter.generate(payload))
            snapshot = {"entries": [{"id": item.id, "version": item.version} for item in payload.controlled_knowledge]}
            _validate_output(output, snapshot, payload)
            results.append({
                "case_id": case["id"], "contract": guidance_adapter.descriptor.prompt_contract_version,
                "latency_ms": round((clock() - started) * 1000, 3),
                "error_codes": [], "recorded_output": output.model_dump(mode="json"),
            })
        except (AdapterError, GuidanceExecutionError) as exc:
            results.append({
                "case_id": case["id"], "contract": guidance_adapter.descriptor.prompt_contract_version,
                "latency_ms": round((clock() - started) * 1000, 3),
                "error_codes": [exc.code], "recorded_output": None,
            })

    evaluated = [item for item in results if item["error_codes"] != ["ANALYSIS_BLOCKED_BY_SAFETY"]]
    return {
        **plan,
        "adapter_descriptors": {
            **({"understanding": understanding_adapter.descriptor.model_dump()} if understanding_cases else {}),
            **({"guidance": guidance_adapter.descriptor.model_dump()} if guidance_cases else {}),
        },
        "requests_sent": len(evaluated),
        "execution_completed": True,
        "hard_gate_passed": all(not item["error_codes"] for item in evaluated),
        "human_review_required": True,
        "qualification_status": "PENDING_HUMAN_REVIEW",
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Budgeted dual-contract live Qwen qualification")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = run_live_qualification(
            args.dataset,
            execute=args.execute,
            authorized=os.getenv(AUTH_ENV) == "YES",
        )
    except (PermissionError, RuntimeError, ValueError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not args.execute or report["hard_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
