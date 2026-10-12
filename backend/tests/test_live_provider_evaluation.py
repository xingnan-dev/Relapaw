from pathlib import Path

import pytest

from app.evaluation.live_provider import run_live_dataset
from app.schemas.analysis import AdapterDescriptor, UnderstandingOutput
from app.services.understanding_adapter import AdapterError


DATASET = Path(__file__).parents[1] / "evals" / "live_provider_v1.json"


class FakeLiveAdapter:
    descriptor = AdapterDescriptor(
        adapter_name="fake-live",
        model_provider="test",
        model_name="fixture",
        model_version="v1",
        prompt_contract_version="text-understanding/v5-grounded-claims",
    )

    def __init__(self, error_code: str | None = None):
        self.calls = 0
        self.error_code = error_code

    def analyze(self, payload):
        self.calls += 1
        if self.error_code:
            raise AdapterError(self.error_code, "recorded test failure")
        evidence_key = payload.evidence[0].key
        is_chinese = payload.raw_owner_input.startswith("小狗")
        return UnderstandingOutput.model_validate(
            {
                "claims": [
                    {
                        "claim_type": "BEHAVIORAL_CONTEXT",
                        "statement": (
                            "这次停留可能与对门外环境的短暂关注有关。"
                            if is_chinese
                            else "The glances may reflect brief attention toward the hallway."
                        ),
                        "confidence_label": "LOW",
                        "evidence": [{"evidence_key": evidence_key, "role": "SUPPORTS"}],
                        "uncertainties": [
                            {
                                "kind": "MISSING_CONTEXT",
                                "description": (
                                    "没有记录当时门外的环境。"
                                    if is_chinese
                                    else "The hallway context was not recorded."
                                ),
                            }
                        ],
                    }
                ]
            }
        )


def test_default_mode_is_dry_run_and_sends_no_requests() -> None:
    adapter = FakeLiveAdapter()

    report = run_live_dataset(DATASET, adapter=adapter)

    assert report["mode"] == "dry-run"
    assert report["requests_sent"] == 0
    assert report["database_writes"] == 0
    assert adapter.calls == 0


def test_execute_requires_separate_authorization() -> None:
    with pytest.raises(PermissionError):
        run_live_dataset(DATASET, execute=True, authorized=False, adapter=FakeLiveAdapter())


def test_authorized_fake_run_respects_request_budget_and_hard_gates() -> None:
    adapter = FakeLiveAdapter()
    ticks = iter([1.0, 1.01, 2.0, 2.02])

    report = run_live_dataset(
        DATASET,
        execute=True,
        authorized=True,
        adapter=adapter,
        clock=lambda: next(ticks),
    )

    assert adapter.calls == 2
    assert report["requests_sent"] == 2
    assert report["retries"] == 0
    assert report["database_writes"] == 0
    assert report["hard_gate_passed"] is True
    assert report["human_review_required"] is True


def test_fake_provider_error_is_reported_without_retry() -> None:
    adapter = FakeLiveAdapter("MODEL_TIMEOUT")

    report = run_live_dataset(DATASET, execute=True, authorized=True, adapter=adapter)

    assert adapter.calls == 2
    assert report["hard_gate_passed"] is False
    assert all(result["error_codes"] == ["MODEL_TIMEOUT"] for result in report["results"])
