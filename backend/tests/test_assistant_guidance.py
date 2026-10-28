import pytest

from app.api.routes.capabilities import get_ai_enabled
from app.domain.educational_knowledge import KNOWLEDGE_SET, approved_knowledge_entries
from app.schemas.assistant import AssistantGuidanceDescriptor, AssistantGuidanceInput, AssistantGuidanceOutput
from app.services.assistant_adapter import get_assistant_guidance_adapter
from app.services.assistant_guidance import GuidanceExecutionError, _validate_output
from sqlalchemy import text


class FakeGuidanceAdapter:
    descriptor = AssistantGuidanceDescriptor(
        adapter_name="fake-guidance", model_provider="test", model_name="fixture",
        model_version="fixture-v1", prompt_contract_version="assistant-guidance/test-v1",
    )

    def __init__(self, *, invalid_citation: bool = False, record_lineage: str = "valid", output_issue: str | None = None, before_return=None):
        self.calls = 0
        self.invalid_citation = invalid_citation
        self.record_lineage = record_lineage
        self.output_issue = output_issue
        self.last_input = None
        self.before_return = before_return

    def generate(self, payload):
        self.calls += 1
        self.last_input = payload
        if self.before_return:
            self.before_return()
        knowledge_id = "outside-runtime-set" if self.invalid_citation else payload.controlled_knowledge[0].id
        record_sources = [
            {"section": "records_show", "item_index": 0, "episode_ids": [payload.current_record.episode_id]},
            *([{"section": "owner_interpretation", "item_index": 0, "episode_ids": [payload.current_record.episode_id]}] if payload.current_record.owner_interpretations else []),
        ]
        if self.record_lineage == "missing":
            record_sources = []
        elif self.record_lineage == "outside-input":
            record_sources[0]["episode_ids"] = [payload.current_record.episode_id + 999_999]
        background = ["Repeated factual records can be compared without identifying a cause."]
        contact = ["Contact a veterinarian if a new urgent concern appears or the situation worsens."]
        sources = [
            {"citation_id": f"knowledge:{knowledge_id}@{payload.controlled_knowledge[0].version}", "knowledge_id": knowledge_id, "knowledge_version": payload.controlled_knowledge[0].version, "supports_section": "possibly_relevant_background", "item_index": 0},
            {"citation_id": f"knowledge:{knowledge_id}@{payload.controlled_knowledge[0].version}", "knowledge_id": knowledge_id, "knowledge_version": payload.controlled_knowledge[0].version, "supports_section": "continue_observing", "item_index": 0},
        ]
        if self.output_issue == "missing_item_citation":
            background.append("A second uncited item.")
        elif self.output_issue == "safety_restatement":
            background = ["Safety status is NORMAL."]
        elif self.output_issue == "medical_detail":
            contact = ["Contact a veterinarian if appetite changes or pain appears."]
        return AssistantGuidanceOutput(
            records_show=[payload.current_record.observations[0]],
            owner_interpretation=payload.current_record.owner_interpretations,
            possibly_relevant_background=background,
            cannot_determine=["The cause cannot be determined from these records."],
            continue_observing=["Record time, place and duration in the same way."],
            contact_vet_when=contact,
            sources_used=sources,
            record_sources=record_sources,
        )


def create_episode(client, pet, *, safety="NORMAL"):
    return client.post("/api/v1/episodes/complete", json={
        "pet_id": pet["id"], "happened_at": "2026-10-25T08:00:00Z", "episode_type": "observation",
        "raw_owner_input": "Stayed beside the door for 30 seconds",
        "observations": [{"behavior_type": "resting", "description": "Stayed beside the door", "source_type": "owner_direct"}],
        "owner_interpretations": [{"interpretation": "May have been waiting"}],
        "safety_check": {"result": safety, "danger_signals": [] if safety == "NORMAL" else ["other_urgent_concern"], "acknowledged_at": "2026-10-25T08:01:00Z"},
    }).json()


def enable_fake(client, adapter):
    client.app.dependency_overrides[get_ai_enabled] = lambda: True
    client.app.dependency_overrides[get_assistant_guidance_adapter] = lambda: adapter


def test_guidance_uses_only_approved_knowledge_and_persists_seven_section_lineage(client, pet):
    episode = create_episode(client, pet)
    adapter = FakeGuidanceAdapter()
    enable_fake(client, adapter)
    response = client.post(f"/api/v1/episodes/{episode['id']}/assistant-guidance-runs", json={
        "request_id": "guidance-1", "mode": "RECORD_REVIEW",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["input_contract_version"] == "assistant-guidance-input/v1"
    assert body["output_contract_version"] == "assistant-guidance-output/v4"
    assert body["knowledge_snapshot"]["set_version"] == KNOWLEDGE_SET["version"]
    assert body["knowledge_snapshot"]["entries"]
    assert all(item["review_status"] == "APPROVED" and item["withdrawn_at"] is None for item in body["knowledge_snapshot"]["entries"])
    assert set(body["normalized_output"]) == {
        "contract_version", "records_show", "owner_interpretation", "possibly_relevant_background",
        "cannot_determine", "continue_observing", "contact_vet_when", "sources_used", "record_sources",
    }
    assert adapter.calls == 1
    assert adapter.last_input.current_record.raw_owner_input == "Stayed beside the door for 30 seconds"
    exported = client.get("/api/v1/privacy/export")
    assert exported.status_code == 200
    assert exported.json()["assistant_guidance_runs"][0]["knowledge_snapshot"]["set_version"] == KNOWLEDGE_SET["version"]


def test_non_normal_safety_blocks_before_guidance_adapter(client, pet):
    episode = create_episode(client, pet, safety="ESCALATE_TO_VET")
    adapter = FakeGuidanceAdapter()
    client.app.dependency_overrides[get_assistant_guidance_adapter] = lambda: adapter
    response = client.post(f"/api/v1/episodes/{episode['id']}/assistant-guidance-runs", json={
        "request_id": "blocked-1", "mode": "VET_TIMELINE",
    })
    assert response.status_code == 201
    assert response.json()["status"] == "BLOCKED_BY_SAFETY"
    assert response.json()["normalized_output"] is None
    assert adapter.calls == 0


def test_safety_change_while_provider_runs_discards_generated_output(client, pet):
    episode = create_episode(client, pet)
    def escalate():
        with client.app.state.test_engine.begin() as connection:
            connection.execute(text("UPDATE safety_checks SET result='ESCALATE_TO_VET' WHERE episode_id=:episode_id"), {"episode_id": episode["id"]})
    adapter = FakeGuidanceAdapter(before_return=escalate)
    enable_fake(client, adapter)
    response = client.post(f"/api/v1/episodes/{episode['id']}/assistant-guidance-runs", json={
        "request_id": "safety-race", "mode": "RECORD_REVIEW",
    })
    assert response.status_code == 201
    assert response.json()["status"] == "BLOCKED_BY_SAFETY"
    assert response.json()["normalized_output"] is None
    assert adapter.calls == 1


def test_unapproved_citation_rejects_output_and_keeps_failed_audit_run(client, pet):
    episode = create_episode(client, pet)
    adapter = FakeGuidanceAdapter(invalid_citation=True)
    enable_fake(client, adapter)
    response = client.post(f"/api/v1/episodes/{episode['id']}/assistant-guidance-runs", json={
        "request_id": "bad-citation", "mode": "RECENT_CHANGE_COMPARISON",
    })
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "MODEL_KNOWLEDGE_CITATION_INVALID"
    history = client.get(f"/api/v1/episodes/{episode['id']}/assistant-guidance-runs").json()
    assert history[0]["status"] == "FAILED"
    assert history[0]["normalized_output"] is None


def test_missing_record_lineage_rejects_output_and_keeps_failed_audit_run(client, pet):
    episode = create_episode(client, pet)
    adapter = FakeGuidanceAdapter(record_lineage="missing")
    enable_fake(client, adapter)

    response = client.post(f"/api/v1/episodes/{episode['id']}/assistant-guidance-runs", json={
        "request_id": "missing-lineage", "mode": "RECORD_REVIEW",
    })

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "MODEL_RECORD_LINEAGE_MISSING"
    history = client.get(f"/api/v1/episodes/{episode['id']}/assistant-guidance-runs").json()
    assert history[0]["status"] == "FAILED"
    assert history[0]["normalized_output"] is None


def test_record_lineage_outside_supplied_input_is_rejected(client, pet):
    episode = create_episode(client, pet)
    adapter = FakeGuidanceAdapter(record_lineage="outside-input")
    enable_fake(client, adapter)

    response = client.post(f"/api/v1/episodes/{episode['id']}/assistant-guidance-runs", json={
        "request_id": "outside-lineage", "mode": "VET_TIMELINE",
    })

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "MODEL_RECORD_LINEAGE_INVALID"
    history = client.get(f"/api/v1/episodes/{episode['id']}/assistant-guidance-runs").json()
    assert history[0]["status"] == "FAILED"
    assert history[0]["normalized_output"] is None


@pytest.mark.parametrize(("issue", "code"), [
    ("missing_item_citation", "MODEL_KNOWLEDGE_CITATION_MISSING"),
    ("safety_restatement", "MODEL_SAFETY_RESTATEMENT"),
    ("medical_detail", "MODEL_UNAPPROVED_MEDICAL_DETAIL"),
])
def test_guidance_semantic_boundaries_reject_unreliable_output(client, pet, issue, code):
    episode = create_episode(client, pet)
    enable_fake(client, FakeGuidanceAdapter(output_issue=issue))
    response = client.post(f"/api/v1/episodes/{episode['id']}/assistant-guidance-runs", json={
        "request_id": f"boundary-{issue}", "mode": "RECORD_REVIEW",
    })
    assert response.status_code == 502
    assert response.json()["error"]["code"] == code


def test_deleting_source_record_removes_guidance_and_its_snapshots(client, pet):
    episode = create_episode(client, pet)
    adapter = FakeGuidanceAdapter()
    enable_fake(client, adapter)
    assert client.post(f"/api/v1/episodes/{episode['id']}/assistant-guidance-runs", json={
        "request_id": "delete-me", "mode": "RECORD_REVIEW",
    }).status_code == 201
    assert client.delete(f"/api/v1/episodes/{episode['id']}").status_code == 204
    with client.app.state.test_engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM assistant_guidance_runs")) == 0


def test_withdrawn_knowledge_never_enters_runtime_subset():
    entry = KNOWLEDGE_SET["entries"][0]
    previous_status, previous_withdrawn = entry["review_status"], entry["withdrawn_at"]
    try:
        entry["review_status"] = "WITHDRAWN"
        entry["withdrawn_at"] = "2026-10-25"
        assert entry["id"] not in {item["id"] for item in approved_knowledge_entries(species="cat")}
    finally:
        entry["review_status"], entry["withdrawn_at"] = previous_status, previous_withdrawn


def _validation_input(*, with_knowledge: bool = True):
    knowledge = [{
        "id": "context", "version": "v1", "citation_id": "knowledge:context@v1",
        "title": "Recording context", "summary": "Record time and place",
        "source_title": "Controlled guide", "source_locator": "context",
    }] if with_knowledge else []
    return AssistantGuidanceInput.model_validate({
        "mode": "RECORD_REVIEW", "pet_id": 1, "species": "dog",
        "current_record": {"episode_id": 1, "happened_at": "2026-10-26T00:00:00Z", "raw_owner_input": "Waited.", "observations": ["Waited"], "owner_interpretations": [], "safety_status": "NORMAL"},
        "recent_records": [], "recent_records_truncated": False, "controlled_knowledge": knowledge,
    })


def _validation_output(*, background=None, observing=None, sources=None):
    return AssistantGuidanceOutput.model_validate({
        "records_show": ["Waited"], "owner_interpretation": [],
        "possibly_relevant_background": background or [], "cannot_determine": ["Cannot determine a cause."],
        "continue_observing": observing or [], "contact_vet_when": ["Contact a veterinarian if a new urgent concern appears or the situation worsens."],
        "sources_used": sources or [],
        "record_sources": [{"section": "records_show", "item_index": 0, "episode_ids": [1]}],
    })


def test_versioned_citation_must_match_exact_approved_snapshot_entry():
    payload = _validation_input()
    output = _validation_output(
        background=["Record context consistently."],
        sources=[{"citation_id": "knowledge:context@v2", "knowledge_id": "context", "knowledge_version": "v2", "supports_section": "possibly_relevant_background", "item_index": 0}],
    )
    with pytest.raises(GuidanceExecutionError, match="outside the approved runtime set") as error:
        _validate_output(output, {"entries": [{"id": "context", "version": "v1"}]}, payload)
    assert error.value.code == "MODEL_KNOWLEDGE_CITATION_INVALID"


def test_no_approved_knowledge_allows_explicit_uncertainty_but_no_advice():
    payload = _validation_input(with_knowledge=False)
    safe_output = _validation_output()
    _validate_output(safe_output, {"entries": []}, payload)

    uncited_advice = _validation_output(observing=["Keep a log."])
    with pytest.raises(GuidanceExecutionError) as error:
        _validate_output(uncited_advice, {"entries": []}, payload)
    assert error.value.code == "MODEL_KNOWLEDGE_CITATION_INVALID"
