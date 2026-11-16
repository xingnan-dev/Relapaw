from pathlib import Path

import pytest

from app.evaluation.live_qualification import run_live_qualification
from app.schemas.analysis import AdapterDescriptor, UnderstandingOutput
from app.schemas.assistant import AssistantGuidanceDescriptor, AssistantGuidanceOutput


DATASET = Path(__file__).parents[1] / "evals" / "live_qualification_qwen_beijing_v4.json"
MODEL = "qwen3.7-plus-2026-05-26"


class FakeUnderstandingAdapter:
    def __init__(self, *, model: str = MODEL):
        self.calls = 0
        self.descriptor = AdapterDescriptor(
            adapter_name="qwen-openai-chat-completions", model_provider="qwen",
            model_name=model, model_version=model,
            prompt_contract_version="text-understanding/v7-verbatim-fact-extraction",
        )

    def analyze(self, payload):
        self.calls += 1
        evidence = next(item for item in payload.evidence if item.source_type == "RAW_OWNER_INPUT")
        if payload.raw_owner_input.startswith("小狗"):
            observation, interpretation = payload.raw_owner_input.split("。", 1)
            observations = [{"source_quote": observation + "。", "evidence_key": evidence.key}]
            interpretations = [{"source_quote": interpretation, "evidence_key": evidence.key}] if interpretation else []
        else:
            observation, interpretation = payload.raw_owner_input.split(" I think", 1)
            observations = [{"source_quote": observation, "evidence_key": evidence.key}]
            interpretations = [{"source_quote": "I think" + interpretation, "evidence_key": evidence.key}]
        return UnderstandingOutput.model_validate({
            "observation_candidates": observations,
            "owner_interpretations": interpretations,
        })


class FakeGuidanceAdapter:
    def __init__(self, *, invalid_lineage: bool = False, model: str = MODEL):
        self.calls = 0
        self.invalid_lineage = invalid_lineage
        self.descriptor = AssistantGuidanceDescriptor(
            adapter_name="qwen-openai-chat-guidance", model_provider="qwen",
            model_name=model, model_version=model,
            prompt_contract_version="assistant-guidance/v4-versioned-claim-citations",
        )

    def generate(self, payload):
        self.calls += 1
        chinese = payload.current_record.raw_owner_input.startswith("小狗")
        episode_id = payload.current_record.episode_id + (999_999 if self.invalid_lineage else 0)
        owner = payload.current_record.owner_interpretations
        return AssistantGuidanceOutput.model_validate({
            "records_show": [payload.current_record.observations[0]],
            "owner_interpretation": owner,
            "possibly_relevant_background": ["一致记录有助比较。" if chinese else "Consistent records support comparison."],
            "cannot_determine": ["不能确定原因。" if chinese else "The cause cannot be determined from these records."],
            "continue_observing": ["继续按相同方式记录。" if chinese else "Continue recording in the same way."],
            "contact_vet_when": ["出现新的紧急情况或恶化时联系兽医。" if chinese else "Contact a veterinarian if an urgent concern appears or the situation worsens."],
            "sources_used": [
                {"citation_id": "knowledge:recording-consistency@v1", "knowledge_id": "recording-consistency", "knowledge_version": "v1", "supports_section": "possibly_relevant_background", "item_index": 0},
                {"citation_id": "knowledge:recording-consistency@v1", "knowledge_id": "recording-consistency", "knowledge_version": "v1", "supports_section": "continue_observing", "item_index": 0},
            ],
            "record_sources": [
                {"section": "records_show", "item_index": 0, "episode_ids": [episode_id]},
                *([{"section": "owner_interpretation", "item_index": 0, "episode_ids": [payload.current_record.episode_id]}] if owner else []),
            ],
        })


def test_live_qualification_defaults_to_zero_request_dry_run():
    understanding, guidance = FakeUnderstandingAdapter(), FakeGuidanceAdapter()

    report = run_live_qualification(
        DATASET, understanding_adapter=understanding, guidance_adapter=guidance,
    )

    assert report["mode"] == "dry-run"
    assert report["planned_requests"] == 2
    assert report["requests_sent"] == 0
    assert report["database_writes"] == 0
    assert understanding.calls == guidance.calls == 0


def test_live_qualification_requires_separate_explicit_authorization():
    with pytest.raises(PermissionError):
        run_live_qualification(
            DATASET, execute=True, authorized=False,
            understanding_adapter=FakeUnderstandingAdapter(), guidance_adapter=FakeGuidanceAdapter(),
        )


def test_live_qualification_rejects_model_drift_before_any_request():
    understanding = FakeUnderstandingAdapter()
    guidance = FakeGuidanceAdapter(model="moving-alias")

    with pytest.raises(ValueError, match="frozen qualification subject"):
        run_live_qualification(
            DATASET, execute=True, authorized=True,
            understanding_adapter=understanding, guidance_adapter=guidance,
        )

    assert understanding.calls == guidance.calls == 0


def test_authorized_fake_run_covers_both_contracts_and_requires_human_review():
    understanding, guidance = FakeUnderstandingAdapter(), FakeGuidanceAdapter()
    ticks = iter(float(value) for value in range(8))

    report = run_live_qualification(
        DATASET, execute=True, authorized=True,
        understanding_adapter=understanding, guidance_adapter=guidance,
        clock=lambda: next(ticks),
    )

    assert understanding.calls == 0
    assert guidance.calls == 2
    assert report["requests_sent"] == 2
    assert report["retries"] == 0
    assert report["database_writes"] == 0
    assert report["hard_gate_passed"] is True
    assert report["human_review_required"] is True
    assert report["qualification_status"] == "PENDING_HUMAN_REVIEW"
    assert {item["contract"] for item in report["results"]} == {
        "assistant-guidance/v4-versioned-claim-citations",
    }


def test_guidance_lineage_failure_fails_the_qualification_gate():
    report = run_live_qualification(
        DATASET, execute=True, authorized=True,
        understanding_adapter=FakeUnderstandingAdapter(),
        guidance_adapter=FakeGuidanceAdapter(invalid_lineage=True),
    )

    assert report["hard_gate_passed"] is False
    guidance_results = [item for item in report["results"] if item["contract"] == "assistant-guidance/v4-versioned-claim-citations"]
    assert all(item["error_codes"] == ["MODEL_RECORD_LINEAGE_INVALID"] for item in guidance_results)
