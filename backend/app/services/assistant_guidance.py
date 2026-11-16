import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.errors import APIError
from app.domain.educational_knowledge import knowledge_snapshot
from app.models import AssistantGuidanceRun, Episode
from app.schemas.assistant import (
    AssistantGuidanceInput,
    AssistantGuidanceOutput,
    GuidanceKnowledgeInput,
    GuidanceRecordInput,
    GuidanceRunCreate,
)
from app.services.assistant_adapter import AssistantGuidanceAdapter
from app.services.understanding_adapter import AdapterError


RUN_LOADS = (joinedload(AssistantGuidanceRun.episode),)
_FORBIDDEN_DIRECTIVE = re.compile(
    r"诊断为|确诊|服用|给药|剂量|毫克|治疗方案|替代兽医|\bdiagnos(?:e|ed)\s+as\b|\b(?:dose|dosage)\b|\b\d+(?:\.\d+)?\s*mg\b|\bprescrib",
    re.IGNORECASE,
)
_SAFETY_RESTATEMENT = re.compile(
    r"(?:safety\s+(?:status|check)|\bnormal\b|安全(?:状态|检查)|当前安全|状态正常|安全正常)", re.IGNORECASE,
)
_UNAPPROVED_MEDICAL_DETAIL = re.compile(
    r"(?:疼痛|食欲|呕吐|腹泻|呼吸|出血|抽搐|排尿|症状|频率|强度|\bpain\b|\bappetite\b|\bvomit|\bdiarrh|\bbreath|\bbleed|\bseizure|\burinat|\bsymptom|\bfrequency\b|\bintensity\b)",
    re.IGNORECASE,
)


@dataclass
class GuidanceExecutionError(Exception):
    code: str
    message: str
    status_code: int


def _record_input(episode: Episode) -> GuidanceRecordInput:
    return GuidanceRecordInput(
        episode_id=episode.id,
        happened_at=episode.happened_at,
        raw_owner_input=episode.raw_owner_input,
        observations=[item.description for item in episode.observations],
        owner_interpretations=[item.interpretation for item in episode.owner_interpretations],
        safety_status=episode.safety_check.result if episode.safety_check is not None else "NOT_CHECKED",
    )


def build_guidance_input(db: Session, episode: Episode, mode: str) -> tuple[AssistantGuidanceInput, dict]:
    snapshot = knowledge_snapshot(species=episode.pet.species)
    recent = list(db.scalars(
        select(Episode)
        .where(Episode.pet_id == episode.pet_id, Episode.deleted_at.is_(None), Episode.id != episode.id)
        .options(selectinload(Episode.observations), selectinload(Episode.owner_interpretations))
        .order_by(Episode.happened_at.desc(), Episode.id.desc())
        .limit(101)
    ).all())
    knowledge = [GuidanceKnowledgeInput(
        id=item["id"], version=item["version"], citation_id=f'knowledge:{item["id"]}@{item["version"]}', title=item["title"], summary=item["summary"],
        source_title=item["source"]["title"], source_locator=item["source"]["locator"],
    ) for item in snapshot["entries"]]
    return AssistantGuidanceInput(
        mode=mode, pet_id=episode.pet_id, species=episode.pet.species,
        current_record=_record_input(episode), recent_records=[_record_input(item) for item in recent[:100]],
        recent_records_truncated=len(recent) > 100,
        controlled_knowledge=knowledge,
    ), snapshot


def _validate_output(output: AssistantGuidanceOutput, knowledge: dict, input_data: AssistantGuidanceInput) -> None:
    allowed = {
        f'knowledge:{item["id"]}@{item["version"]}': (item["id"], item["version"])
        for item in knowledge["entries"]
    }
    if any(
        allowed.get(item.citation_id) != (item.knowledge_id, item.knowledge_version)
        for item in output.sources_used
    ):
        raise GuidanceExecutionError("MODEL_KNOWLEDGE_CITATION_INVALID", "Model cited knowledge outside the approved runtime set", 502)
    if not allowed and (output.possibly_relevant_background or output.continue_observing or output.sources_used):
        raise GuidanceExecutionError("MODEL_KNOWLEDGE_CITATION_INVALID", "Model generated knowledge claims without approved runtime knowledge", 502)
    for section_name in ("possibly_relevant_background", "continue_observing", "contact_vet_when"):
        values = getattr(output, section_name)
        cited_indexes = set()
        for citation in output.sources_used:
            if citation.supports_section != section_name:
                continue
            if citation.item_index >= len(values):
                raise GuidanceExecutionError("MODEL_KNOWLEDGE_CITATION_INVALID", "Model citation item index is outside the generated section", 502)
            cited_indexes.add(citation.item_index)
        if section_name != "contact_vet_when" and cited_indexes != set(range(len(values))):
            raise GuidanceExecutionError("MODEL_KNOWLEDGE_CITATION_MISSING", "Model guidance did not include complete item-level knowledge citations", 502)
    allowed_episode_ids = {input_data.current_record.episode_id, *(item.episode_id for item in input_data.recent_records)}
    for section_name in ("records_show", "owner_interpretation"):
        values = getattr(output, section_name)
        mapped_indexes = set()
        for source in output.record_sources:
            if source.section != section_name:
                continue
            if source.item_index >= len(values) or not set(source.episode_ids).issubset(allowed_episode_ids):
                raise GuidanceExecutionError("MODEL_RECORD_LINEAGE_INVALID", "Model referenced records outside the supplied input", 502)
            mapped_indexes.add(source.item_index)
        if mapped_indexes != set(range(len(values))):
            raise GuidanceExecutionError("MODEL_RECORD_LINEAGE_MISSING", "Model record statements did not include complete source lineage", 502)
    visible_text = "\n".join(
        output.records_show + output.owner_interpretation + output.possibly_relevant_background
        + output.cannot_determine + output.continue_observing + output.contact_vet_when
    )
    if _FORBIDDEN_DIRECTIVE.search(visible_text):
        raise GuidanceExecutionError("MODEL_SAFETY_POLICY_VIOLATION", "Model output crossed the non-diagnostic safety boundary", 502)
    if _SAFETY_RESTATEMENT.search(visible_text):
        raise GuidanceExecutionError("MODEL_SAFETY_RESTATEMENT", "Model output restated or reinterpreted the separate safety check", 502)
    if _UNAPPROVED_MEDICAL_DETAIL.search("\n".join(output.contact_vet_when)):
        raise GuidanceExecutionError("MODEL_UNAPPROVED_MEDICAL_DETAIL", "Model output added medical detail without approved medical knowledge", 502)


def get_guidance_run(db: Session, run_id: int) -> AssistantGuidanceRun | None:
    return db.scalar(select(AssistantGuidanceRun).where(AssistantGuidanceRun.id == run_id).options(*RUN_LOADS))


def list_guidance_runs(db: Session, episode_id: int) -> list[AssistantGuidanceRun]:
    return list(db.scalars(
        select(AssistantGuidanceRun).where(AssistantGuidanceRun.episode_id == episode_id)
        .options(*RUN_LOADS).order_by(AssistantGuidanceRun.created_at.desc(), AssistantGuidanceRun.id.desc())
    ).all())


def execute_guidance(db: Session, episode: Episode, payload: GuidanceRunCreate, adapter: AssistantGuidanceAdapter) -> AssistantGuidanceRun:
    existing = db.scalar(select(AssistantGuidanceRun).where(
        AssistantGuidanceRun.episode_id == episode.id,
        AssistantGuidanceRun.request_id == payload.request_id,
    ).options(*RUN_LOADS))
    if existing is not None:
        created = existing.created_at.replace(tzinfo=timezone.utc) if existing.created_at.tzinfo is None else existing.created_at
        if existing.status == "RUNNING" and created <= datetime.now(timezone.utc) - timedelta(minutes=5):
            existing.status = "FAILED"
            existing.error_code = "ANALYSIS_INTERRUPTED"
            existing.completed_at = datetime.now(timezone.utc)
            db.flush()
        return existing

    input_data, snapshot = build_guidance_input(db, episode, payload.mode)
    descriptor = adapter.descriptor
    run = AssistantGuidanceRun(
        episode_id=episode.id, request_id=payload.request_id, mode=payload.mode,
        status="BLOCKED_BY_SAFETY" if episode.safety_check is None or episode.safety_check.result != "NORMAL" else "RUNNING",
        adapter_name=descriptor.adapter_name, model_provider=descriptor.model_provider,
        model_name=descriptor.model_name, model_version=descriptor.model_version,
        prompt_contract_version=descriptor.prompt_contract_version,
        input_contract_version=descriptor.input_contract_version,
        output_contract_version=descriptor.output_contract_version,
        input_snapshot=input_data.model_dump(mode="json"), knowledge_snapshot=snapshot,
        error_code="ANALYSIS_BLOCKED_BY_SAFETY" if episode.safety_check is None or episode.safety_check.result != "NORMAL" else None,
        source_episode_updated_at=episode.updated_at,
        completed_at=datetime.now(timezone.utc) if episode.safety_check is None or episode.safety_check.result != "NORMAL" else None,
    )
    db.add(run)
    db.flush()
    if run.status == "BLOCKED_BY_SAFETY":
        return get_guidance_run(db, run.id) or run
    run_id = run.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        concurrent = db.scalar(select(AssistantGuidanceRun).where(
            AssistantGuidanceRun.episode_id == episode.id,
            AssistantGuidanceRun.request_id == payload.request_id,
        ).options(*RUN_LOADS))
        if concurrent is None:
            raise
        return concurrent

    try:
        output = AssistantGuidanceOutput.model_validate(adapter.generate(input_data))
        _validate_output(output, snapshot, input_data)
    except AdapterError as exc:
        current = db.get(AssistantGuidanceRun, run_id)
        if current is not None:
            current.status, current.error_code, current.completed_at = "FAILED", exc.code, datetime.now(timezone.utc)
            db.flush()
        raise GuidanceExecutionError(exc.code, exc.message, exc.status_code)
    except ValidationError as exc:
        current = db.get(AssistantGuidanceRun, run_id)
        if current is not None:
            current.status, current.error_code, current.completed_at = "FAILED", "MODEL_OUTPUT_INVALID", datetime.now(timezone.utc)
            db.flush()
        raise GuidanceExecutionError("MODEL_OUTPUT_INVALID", "Model output did not match the required contract", 502) from exc
    except GuidanceExecutionError as exc:
        current = db.get(AssistantGuidanceRun, run_id)
        if current is not None:
            current.status, current.error_code, current.completed_at = "FAILED", exc.code, datetime.now(timezone.utc)
            db.flush()
        raise
    except Exception as exc:
        current = db.get(AssistantGuidanceRun, run_id)
        if current is not None:
            current.status, current.error_code, current.completed_at = "FAILED", "MODEL_PROVIDER_ERROR", datetime.now(timezone.utc)
            db.flush()
        raise GuidanceExecutionError("MODEL_PROVIDER_ERROR", "Model provider request failed", 502) from exc

    current = db.scalar(select(AssistantGuidanceRun).where(AssistantGuidanceRun.id == run_id).with_for_update())
    live_episode = db.scalar(select(Episode).where(Episode.id == episode.id, Episode.deleted_at.is_(None)).with_for_update())
    if current is None or live_episode is None:
        db.rollback()
        raise GuidanceExecutionError("ANALYSIS_SOURCE_DELETED", "The source record was deleted while guidance was running", 409)
    db.expire(live_episode, ["safety_check", "updated_at"])
    if live_episode.safety_check is None or live_episode.safety_check.result != "NORMAL":
        current.status, current.error_code, current.completed_at = "BLOCKED_BY_SAFETY", "ANALYSIS_BLOCKED_BY_SAFETY", datetime.now(timezone.utc)
        current.normalized_output = None
        db.flush()
        return get_guidance_run(db, current.id) or current
    current.status = "COMPLETED"
    current.normalized_output = output.model_dump(mode="json")
    current.error_code = None
    current.model_version = adapter.descriptor.model_version
    current.completed_at = datetime.now(timezone.utc)
    db.flush()
    return get_guidance_run(db, current.id) or current
