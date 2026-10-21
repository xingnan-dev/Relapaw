from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hmac import compare_digest

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.errors import APIError
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    AnalysisRun, BaselineSnapshot, Claim, Episode, EpisodeFollowUp, MemoryCandidate,
    ObservationPlan, Pet, TermsAcceptance, User, UserSession, VeterinaryEscalation,
)
from app.services.sessions import token_digest


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: UserSession


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def require_auth_context(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> AuthContext:
    if not session_token:
        raise APIError(401, "AUTHENTICATION_REQUIRED", "Authentication required")
    stored = db.scalar(
        select(UserSession)
        .where(UserSession.token_hash == token_digest(session_token, settings))
        .options(joinedload(UserSession.user))
    )
    now = datetime.now(UTC)
    if (
        stored is None
        or stored.revoked_at is not None
        or _as_utc(stored.expires_at) <= now
        or _as_utc(stored.last_seen_at) + timedelta(days=settings.session_idle_days) <= now
        or stored.user.status != "ACTIVE"
    ):
        raise APIError(401, "SESSION_INVALID", "Session is invalid or expired")
    if _as_utc(stored.last_seen_at) + timedelta(minutes=5) <= now:
        stored.last_seen_at = now
        db.commit()
    return AuthContext(user=stored.user, session=stored)


def require_current_user(context: AuthContext = Depends(require_auth_context), db: Session = Depends(get_db)) -> User:
    accepted = db.scalar(select(TermsAcceptance.id).where(
        TermsAcceptance.user_id == context.user.id,
        TermsAcceptance.terms_version == settings.terms_version,
        TermsAcceptance.privacy_version == settings.privacy_version,
    ))
    if accepted is None:
        raise APIError(403, "CONSENT_REQUIRED", "Current Terms and Privacy Notice must be accepted")
    return context.user


def require_csrf(
    request: Request,
    context: AuthContext = Depends(require_auth_context),
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> AuthContext:
    origin = request.headers.get("origin")
    if origin not in settings.cors_origins:
        raise APIError(403, "ORIGIN_FORBIDDEN", "Request origin is not allowed")
    if not csrf_token or not compare_digest(
        token_digest(csrf_token, settings), context.session.csrf_token_hash
    ):
        raise APIError(403, "CSRF_INVALID", "CSRF token is missing or invalid")
    return context


def require_pet(db: Session, pet_id: int, user: User, *, for_update: bool = False) -> Pet:
    statement = select(Pet).where(Pet.id == pet_id, Pet.owner_user_id == user.id)
    if for_update:
        statement = statement.with_for_update()
    pet = db.scalar(statement)
    if pet is None:
        raise APIError(404, "PET_NOT_FOUND", "Pet not found")
    return pet


def require_episode(db: Session, episode_id: int, user: User, *, for_update: bool = False) -> Episode:
    statement = select(Episode).join(Pet, Episode.pet_id == Pet.id).where(
        Episode.id == episode_id, Pet.owner_user_id == user.id, Episode.deleted_at.is_(None)
    )
    if for_update:
        # Lock the tenant root and record in one statement. Baseline recomputation
        # uses the same Pet-first serialization boundary.
        statement = statement.with_for_update()
    episode = db.scalar(statement)
    if episode is None:
        raise APIError(404, "EPISODE_NOT_FOUND", "Episode not found")
    return episode


def require_plan(db: Session, plan_id: int, user: User) -> ObservationPlan:
    value = db.scalar(select(ObservationPlan).join(Pet).where(
        ObservationPlan.id == plan_id, Pet.owner_user_id == user.id
    ))
    if value is None:
        raise APIError(404, "OBSERVATION_PLAN_NOT_FOUND", "Observation plan not found")
    return value


def require_follow_up(db: Session, follow_up_id: int, user: User, *, for_update: bool = False) -> EpisodeFollowUp:
    statement = select(EpisodeFollowUp).join(
        Episode, EpisodeFollowUp.source_episode_id == Episode.id
    ).join(Pet, Episode.pet_id == Pet.id).where(
        EpisodeFollowUp.id == follow_up_id, Pet.owner_user_id == user.id
    )
    value = db.scalar(statement)
    if value is None:
        raise APIError(404, "FOLLOW_UP_NOT_FOUND", "Follow-up not found")
    if for_update:
        # Always acquire the source Episode/Pet lock before the follow-up lock;
        # episode redaction follows the same order and cannot race completion.
        source = db.scalar(
            select(Episode)
            .join(Pet, Episode.pet_id == Pet.id)
            .where(Episode.id == value.source_episode_id, Pet.owner_user_id == user.id)
            .with_for_update()
        )
        if source is None:
            raise APIError(404, "FOLLOW_UP_NOT_FOUND", "Follow-up not found")
        value = db.scalar(
            select(EpisodeFollowUp)
            .where(EpisodeFollowUp.id == follow_up_id)
            .with_for_update()
            .options(joinedload(EpisodeFollowUp.source_episode))
        )
        if value is None:
            raise APIError(404, "FOLLOW_UP_NOT_FOUND", "Follow-up not found")
    return value


def require_escalation(db: Session, escalation_id: int, user: User) -> VeterinaryEscalation:
    value = db.scalar(select(VeterinaryEscalation).join(Episode).join(Pet).where(
        VeterinaryEscalation.id == escalation_id, Pet.owner_user_id == user.id
    ))
    if value is None:
        raise APIError(404, "VETERINARY_ESCALATION_NOT_FOUND", "Veterinary escalation not found")
    return value


def require_analysis_run(db: Session, run_id: int, user: User) -> AnalysisRun:
    value = db.scalar(select(AnalysisRun).join(Episode).join(Pet).where(
        AnalysisRun.id == run_id, Pet.owner_user_id == user.id
    ))
    if value is None:
        raise APIError(404, "ANALYSIS_RUN_NOT_FOUND", "Analysis run not found")
    return value


def require_claim(db: Session, claim_id: int, user: User) -> Claim:
    value = db.scalar(select(Claim).join(AnalysisRun).join(Episode).join(Pet).where(
        Claim.id == claim_id, Pet.owner_user_id == user.id
    ))
    if value is None:
        raise APIError(404, "CLAIM_NOT_FOUND", "Claim not found")
    return value


def require_memory_candidate(db: Session, candidate_id: int, user: User) -> MemoryCandidate:
    value = db.scalar(select(MemoryCandidate).join(Pet).where(
        MemoryCandidate.id == candidate_id, Pet.owner_user_id == user.id
    ))
    if value is None:
        raise APIError(404, "MEMORY_CANDIDATE_NOT_FOUND", "Memory candidate not found")
    return value


def require_baseline_snapshot(db: Session, snapshot_id: int, user: User) -> BaselineSnapshot:
    value = db.scalar(select(BaselineSnapshot).join(Pet).where(
        BaselineSnapshot.id == snapshot_id, Pet.owner_user_id == user.id
    ))
    if value is None:
        raise APIError(404, "BASELINE_SNAPSHOT_NOT_FOUND", "Baseline snapshot not found")
    return value
