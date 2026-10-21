from datetime import UTC, date, datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import (
    AnalysisRun, AuditEvent, BaselineEvidence, BaselineSnapshot, Claim, ClaimEvidenceReference,
    Episode, EpisodeFollowUp, EpisodePlanLink, EvidenceReference, LifeEvent,
    MemoryCandidate, MemoryDecision, Observation, ObservationPlan, ObservationPlanItem,
    OwnerInterpretation, OwnerProfile, Pet, PetBaseline, SafetyCheck, TermsAcceptance,
    Uncertainty, User, UserConfirmation, UserIdentity, UserSession, VeterinaryEscalation,
)
from app.services.audit import append_audit_event


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def _row(item: Any, *, exclude: set[str] | None = None) -> dict[str, Any]:
    omitted = exclude or set()
    return {
        column.key: _json_value(getattr(item, column.key))
        for column in sa_inspect(type(item)).columns if column.key not in omitted
    }


def build_account_export(db: Session, user: User, settings: Settings) -> dict[str, Any]:
    pets = list(db.scalars(select(Pet).where(Pet.owner_user_id == user.id)).all())
    pet_ids = [item.id for item in pets]
    all_episode_ids = list(db.scalars(select(Episode.id).where(Episode.pet_id.in_(pet_ids))).all()) if pet_ids else []
    episodes = list(db.scalars(select(Episode).where(
        Episode.pet_id.in_(pet_ids), Episode.deleted_at.is_(None)
    )).all()) if pet_ids else []
    episode_ids = [item.id for item in episodes]
    plans = list(db.scalars(select(ObservationPlan).where(ObservationPlan.pet_id.in_(pet_ids))).all()) if pet_ids else []
    plan_ids = [item.id for item in plans]
    runs = list(db.scalars(select(AnalysisRun).where(AnalysisRun.episode_id.in_(episode_ids))).all()) if episode_ids else []
    run_ids = [item.id for item in runs]
    claims = list(db.scalars(select(Claim).where(Claim.analysis_run_id.in_(run_ids))).all()) if run_ids else []
    claim_ids = [item.id for item in claims]
    candidates = list(db.scalars(select(MemoryCandidate).where(MemoryCandidate.pet_id.in_(pet_ids))).all()) if pet_ids else []
    candidate_ids = [item.id for item in candidates]
    snapshots = list(db.scalars(select(BaselineSnapshot).where(BaselineSnapshot.pet_id.in_(pet_ids))).all()) if pet_ids else []
    snapshot_ids = [item.id for item in snapshots]

    def selected(model, condition):
        return [_row(item) for item in db.scalars(select(model).where(condition)).all()]

    return {
        "format": "relapaw-account-export/v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "policy_versions": {"terms": settings.terms_version, "privacy": settings.privacy_version},
        "account": _row(user, exclude={"deletion_requested_at", "deletion_due_at"}),
        "identities": [_row(item, exclude={"subject"}) for item in db.scalars(select(UserIdentity).where(UserIdentity.user_id == user.id)).all()],
        "consents": selected(TermsAcceptance, TermsAcceptance.user_id == user.id),
        "owner_profiles": selected(OwnerProfile, OwnerProfile.user_id == user.id),
        "pets": [_row(item) for item in pets],
        "pet_baselines": selected(PetBaseline, PetBaseline.pet_id.in_(pet_ids)) if pet_ids else [],
        "life_events": selected(LifeEvent, LifeEvent.pet_id.in_(pet_ids)) if pet_ids else [],
        "observation_plans": [_row(item) for item in plans],
        "observation_plan_items": selected(ObservationPlanItem, ObservationPlanItem.plan_id.in_(plan_ids)) if plan_ids else [],
        "episodes": [_row(item) for item in episodes],
        "observations": selected(Observation, Observation.episode_id.in_(episode_ids)) if episode_ids else [],
        "owner_interpretations": selected(OwnerInterpretation, OwnerInterpretation.episode_id.in_(episode_ids)) if episode_ids else [],
        "safety_checks": selected(SafetyCheck, SafetyCheck.episode_id.in_(episode_ids)) if episode_ids else [],
        "evidence_references": selected(EvidenceReference, EvidenceReference.episode_id.in_(episode_ids)) if episode_ids else [],
        "veterinary_escalations": selected(VeterinaryEscalation, VeterinaryEscalation.episode_id.in_(episode_ids)) if episode_ids else [],
        "episode_plan_links": selected(EpisodePlanLink, EpisodePlanLink.episode_id.in_(episode_ids)) if episode_ids else [],
        "follow_ups": selected(
            EpisodeFollowUp,
            or_(
                EpisodeFollowUp.source_episode_id.in_(all_episode_ids),
                EpisodeFollowUp.result_episode_id.in_(all_episode_ids),
            ),
        ) if all_episode_ids else [],
        "analysis_runs": [_row(item) for item in runs],
        "claims": [_row(item) for item in claims],
        "claim_evidence": selected(ClaimEvidenceReference, ClaimEvidenceReference.claim_id.in_(claim_ids)) if claim_ids else [],
        "uncertainties": selected(Uncertainty, Uncertainty.claim_id.in_(claim_ids)) if claim_ids else [],
        "confirmations": selected(UserConfirmation, UserConfirmation.claim_id.in_(claim_ids)) if claim_ids else [],
        "memory_candidates": [_row(item) for item in candidates],
        "memory_decisions": selected(MemoryDecision, MemoryDecision.candidate_id.in_(candidate_ids)) if candidate_ids else [],
        "baseline_snapshots": [_row(item) for item in snapshots],
        "baseline_evidence": selected(BaselineEvidence, BaselineEvidence.snapshot_id.in_(snapshot_ids)) if snapshot_ids else [],
    }


def request_account_deletion(db: Session, user: User, settings: Settings) -> datetime:
    now = datetime.now(UTC)
    due = now + timedelta(days=settings.account_deletion_grace_days)
    user.status = "PENDING_DELETION"
    user.deletion_requested_at = now
    user.deletion_due_at = due
    db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)).update({"revoked_at": now})
    append_audit_event(db, settings, actor_user_id=user.id, event_type="ACCOUNT_DELETION_REQUESTED", subject_type="USER", subject_id=user.id, metadata={"grace_days": settings.account_deletion_grace_days})
    return due


def redact_episode(db: Session, episode: Episode, user: User, settings: Settings) -> None:
    now = datetime.now(UTC)
    snapshot_ids = list(db.scalars(select(BaselineEvidence.snapshot_id).where(
        BaselineEvidence.episode_id == episode.id
    ).distinct()).all())
    if snapshot_ids:
        db.execute(delete(BaselineSnapshot).where(BaselineSnapshot.id.in_(snapshot_ids)))
    db.execute(delete(AnalysisRun).where(AnalysisRun.episode_id == episode.id))
    db.execute(delete(EpisodePlanLink).where(EpisodePlanLink.episode_id == episode.id))
    db.execute(delete(VeterinaryEscalation).where(VeterinaryEscalation.episode_id == episode.id))
    db.execute(delete(EvidenceReference).where(EvidenceReference.episode_id == episode.id))
    db.execute(delete(SafetyCheck).where(SafetyCheck.episode_id == episode.id))
    db.execute(delete(OwnerInterpretation).where(OwnerInterpretation.episode_id == episode.id))
    db.execute(delete(Observation).where(Observation.episode_id == episode.id))
    db.query(EpisodeFollowUp).filter(
        EpisodeFollowUp.source_episode_id == episode.id,
        EpisodeFollowUp.status == "PENDING",
    ).update({"status": "CANCELLED"})
    episode.happened_at = now
    episode.episode_type = "deleted"
    episode.raw_owner_input = ""
    episode.context = None
    episode.duration_seconds = None
    episode.frequency_count = None
    episode.intensity = None
    episode.location = None
    episode.trigger_context = None
    episode.updated_at = now
    episode.deleted_at = now
    append_audit_event(
        db,
        settings,
        actor_user_id=user.id,
        event_type="EPISODE_CONTENT_DELETED",
        subject_type="EPISODE",
        subject_id=episode.id,
        metadata={"retained_tombstone": True, "removed_snapshot_count": len(snapshot_ids)},
    )


def purge_due_accounts(db: Session, settings: Settings, *, now: datetime | None = None) -> int:
    cutoff = now or datetime.now(UTC)
    users = list(db.scalars(
        select(User).where(
            User.status == "PENDING_DELETION", User.deletion_due_at <= cutoff
        ).with_for_update(skip_locked=True)
    ).all())
    purged = 0
    for user in users:
        append_audit_event(db, settings, actor_user_id=user.id, event_type="ACCOUNT_DATA_PURGED", subject_type="USER", subject_id=user.id)
        pet_ids = list(db.scalars(select(Pet.id).where(Pet.owner_user_id == user.id)).all())
        if pet_ids:
            episode_ids = list(db.scalars(select(Episode.id).where(Episode.pet_id.in_(pet_ids))).all())
            if episode_ids:
                # These two references deliberately use RESTRICT so normal record
                # deletion cannot silently destroy their lifecycle. An account purge
                # is the explicit exception and removes them before the episodes.
                db.execute(delete(EpisodeFollowUp).where(
                    (EpisodeFollowUp.source_episode_id.in_(episode_ids))
                    | (EpisodeFollowUp.result_episode_id.in_(episode_ids))
                ))
                db.execute(delete(AnalysisRun).where(AnalysisRun.episode_id.in_(episode_ids)))
            db.execute(delete(Pet).where(Pet.id.in_(pet_ids)))
        result = db.execute(delete(User).where(User.id == user.id))
        purged += result.rowcount or 0
    db.commit()
    return purged


def purge_expired_audit_events(db: Session, settings: Settings, *, now: datetime | None = None) -> int:
    cutoff = (now or datetime.now(UTC)) - timedelta(days=settings.audit_retention_days)
    result = db.execute(delete(AuditEvent).where(AuditEvent.created_at < cutoff))
    db.commit()
    return result.rowcount or 0
