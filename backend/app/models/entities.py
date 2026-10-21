from datetime import date, datetime, timezone
from uuid import uuid4
from typing import Any, ClassVar

from sqlalchemy import JSON, Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False)
    breed: Mapped[str | None] = mapped_column(String(100))
    birth_date: Mapped[date | None] = mapped_column(Date)
    approximate_age: Mapped[str | None] = mapped_column(String(100))
    sex: Mapped[str | None] = mapped_column(String(30))
    neutered: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    baseline: Mapped["PetBaseline | None"] = relationship(back_populates="pet", cascade="all, delete-orphan")
    episodes: Mapped[list["Episode"]] = relationship(back_populates="pet", cascade="all, delete-orphan")
    life_events: Mapped[list["LifeEvent"]] = relationship(back_populates="pet", cascade="all, delete-orphan")
    observation_plans: Mapped[list["ObservationPlan"]] = relationship(back_populates="pet", cascade="all, delete-orphan")
    memory_candidates: Mapped[list["MemoryCandidate"]] = relationship(back_populates="pet", cascade="all, delete-orphan")
    baseline_snapshots: Mapped[list["BaselineSnapshot"]] = relationship(back_populates="pet", cascade="all, delete-orphan")
    owner: Mapped["User"] = relationship(back_populates="pets")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'PENDING_DELETION', 'DISABLED')", name="ck_user_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletion_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    identities: Mapped[list["UserIdentity"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    terms_acceptances: Mapped[list["TermsAcceptance"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    pets: Mapped[list[Pet]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (UniqueConstraint("provider", "subject", name="uq_user_identity_provider_subject"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship(back_populates="identities")


class IdentityInvitation(Base):
    __tablename__ = "identity_invitations"
    __table_args__ = (
        UniqueConstraint("provider", "subject", name="uq_identity_invitation_provider_subject"),
        CheckConstraint("status IN ('PENDING', 'ACCEPTED', 'REVOKED')", name="ck_identity_invitation_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    accepted_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    user_agent_summary: Mapped[str | None] = mapped_column(String(200))

    user: Mapped[User] = relationship(back_populates="sessions")


class TermsAcceptance(Base):
    __tablename__ = "terms_acceptances"
    __table_args__ = (
        UniqueConstraint("user_id", "terms_version", "privacy_version", name="uq_terms_acceptance_versions"),
        CheckConstraint("source IN ('ONBOARDING', 'VERSION_UPDATE')", name="ck_terms_acceptance_source"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    terms_version: Mapped[str] = mapped_column(String(100), nullable=False)
    privacy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)

    user: Mapped[User] = relationship(back_populates="terms_acceptances")


class OwnerProfile(Base):
    __tablename__ = "owner_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    interaction_preference: Mapped[str | None] = mapped_column(Text)
    observation_preference: Mapped[str | None] = mapped_column(Text)
    response_preference: Mapped[str | None] = mapped_column(Text)
    explanation_preference: Mapped[str | None] = mapped_column(Text)


class PetBaseline(Base):
    __tablename__ = "pet_baselines"

    id: Mapped[int] = mapped_column(primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), unique=True)
    social_behavior: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    activity_pattern: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    feeding_pattern: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    resting_pattern: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    handling_preference: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    hiding_pattern: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    pet: Mapped[Pet] = relationship(back_populates="baseline")


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), index=True)
    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    episode_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_owner_input: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    frequency_count: Mapped[int | None] = mapped_column(Integer)
    intensity: Mapped[int | None] = mapped_column(Integer)
    location: Mapped[str | None] = mapped_column(String(200))
    trigger_context: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    pet: Mapped[Pet] = relationship(back_populates="episodes")
    observations: Mapped[list["Observation"]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    owner_interpretations: Mapped[list["OwnerInterpretation"]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    veterinary_escalations: Mapped[list["VeterinaryEscalation"]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    safety_check: Mapped["SafetyCheck | None"] = relationship(back_populates="episode", cascade="all, delete-orphan")
    evidence_references: Mapped[list["EvidenceReference"]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    plan_links: Mapped[list["EpisodePlanLink"]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    scheduled_follow_ups: Mapped[list["EpisodeFollowUp"]] = relationship(
        back_populates="source_episode", foreign_keys="EpisodeFollowUp.source_episode_id"
    )
    result_of_follow_up: Mapped["EpisodeFollowUp | None"] = relationship(
        back_populates="result_episode", foreign_keys="EpisodeFollowUp.result_episode_id", uselist=False
    )
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="episode")


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    behavior_type: Mapped[str] = mapped_column(String(100), nullable=False)
    standardized_category: Mapped[str | None] = mapped_column(String(30), index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    measured_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(50))
    standardized_unit: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    episode: Mapped[Episode] = relationship(back_populates="observations")


class OwnerInterpretation(Base):
    __tablename__ = "owner_interpretations"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    episode: Mapped[Episode] = relationship(back_populates="owner_interpretations")


class LifeEvent(Base):
    __tablename__ = "life_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    pet: Mapped[Pet] = relationship(back_populates="life_events")


class ObservationPlan(Base):
    __tablename__ = "observation_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    items_to_observe: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    pet: Mapped[Pet] = relationship(back_populates="observation_plans")
    episode_links: Mapped[list["EpisodePlanLink"]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    items: Mapped[list["ObservationPlanItem"]] = relationship(back_populates="plan", cascade="all, delete-orphan", order_by="ObservationPlanItem.sort_order")


class ObservationPlanItem(Base):
    __tablename__ = "observation_plan_items"
    __table_args__ = (UniqueConstraint("plan_id", "sort_order", name="uq_plan_item_sort_order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("observation_plans.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan: Mapped[ObservationPlan] = relationship(back_populates="items")


class VeterinaryEscalation(Base):
    __tablename__ = "veterinary_escalations"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    vet_brief: Mapped[str | None] = mapped_column(Text)
    episode: Mapped[Episode] = relationship(back_populates="veterinary_escalations")


class SafetyCheck(Base):
    __tablename__ = "safety_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), unique=True)
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    danger_signals: Mapped[list[str]] = mapped_column(JSON, default=list)
    other_concern: Mapped[str | None] = mapped_column(Text)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    episode: Mapped[Episode] = relationship(back_populates="safety_check")


class EvidenceReference(Base):
    __tablename__ = "evidence_references"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer)
    field_path: Mapped[str] = mapped_column(String(200), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    episode: Mapped[Episode] = relationship(back_populates="evidence_references")


class EpisodePlanLink(Base):
    __tablename__ = "episode_plan_links"
    __table_args__ = (UniqueConstraint("episode_id", "plan_id", name="uq_episode_plan_link"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("observation_plans.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    episode: Mapped[Episode] = relationship(back_populates="plan_links")
    plan: Mapped[ObservationPlan] = relationship(back_populates="episode_links")


class EpisodeFollowUp(Base):
    __tablename__ = "episode_follow_ups"
    __table_args__ = (
        CheckConstraint("result_episode_id IS NULL OR source_episode_id != result_episode_id", name="ck_follow_up_distinct_episodes"),
        CheckConstraint(
            "(status = 'PENDING' AND result_episode_id IS NULL AND outcome IS NULL AND completed_at IS NULL) OR "
            "(status = 'COMPLETED' AND result_episode_id IS NOT NULL AND outcome IS NOT NULL AND completed_at IS NOT NULL) OR "
            "(status = 'CANCELLED' AND result_episode_id IS NULL AND outcome IS NULL AND completed_at IS NULL)",
            name="ck_follow_up_state_fields",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="RESTRICT"), index=True)
    result_episode_id: Mapped[int | None] = mapped_column(ForeignKey("episodes.id", ondelete="RESTRICT"), unique=True, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source_episode: Mapped[Episode] = relationship(back_populates="scheduled_follow_ups", foreign_keys=[source_episode_id])
    result_episode: Mapped[Episode | None] = relationship(back_populates="result_of_follow_up", foreign_keys=[result_episode_id])


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        UniqueConstraint("episode_id", "request_id", name="uq_analysis_run_episode_request"),
        CheckConstraint("status IN ('RUNNING', 'COMPLETED', 'FAILED', 'BLOCKED_BY_SAFETY')", name="ck_analysis_run_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="RESTRICT"), index=True)
    request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    adapter_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_contract_version: Mapped[str] = mapped_column(String(50), nullable=False)
    input_contract_version: Mapped[str] = mapped_column(String(50), nullable=False)
    output_contract_version: Mapped[str] = mapped_column(String(50), nullable=False)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    normalized_output: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(100))
    source_episode_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    episode: Mapped[Episode] = relationship(back_populates="analysis_runs")
    claims: Mapped[list["Claim"]] = relationship(back_populates="analysis_run", cascade="all, delete-orphan", order_by="Claim.id")

    @property
    def is_stale(self) -> bool:
        source = self.source_episode_updated_at
        current = self.episode.updated_at
        if source.tzinfo is None:
            source = source.replace(tzinfo=timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return current > source


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        CheckConstraint("status IN ('PROPOSED', 'CONFIRMED', 'REJECTED')", name="ck_claim_status"),
        CheckConstraint("confidence_label IN ('LOW', 'MEDIUM', 'HIGH')", name="ck_claim_confidence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True)
    claim_type: Mapped[str] = mapped_column(String(100), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_label: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PROPOSED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="claims")
    evidence_references: Mapped[list["ClaimEvidenceReference"]] = relationship(back_populates="claim", cascade="all, delete-orphan", order_by="ClaimEvidenceReference.id")
    uncertainties: Mapped[list["Uncertainty"]] = relationship(back_populates="claim", cascade="all, delete-orphan", order_by="Uncertainty.id")
    confirmations: Mapped[list["UserConfirmation"]] = relationship(back_populates="claim", cascade="all, delete-orphan", order_by="UserConfirmation.id")
    memory_candidate: Mapped["MemoryCandidate | None"] = relationship(back_populates="claim", cascade="all, delete-orphan", uselist=False)


class ClaimEvidenceReference(Base):
    __tablename__ = "claim_evidence_references"
    __table_args__ = (CheckConstraint("role IN ('SUPPORTS', 'LIMITS', 'CONTEXT')", name="ck_claim_evidence_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    evidence_reference_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_references.id", ondelete="SET NULL"), index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer)
    field_path: Mapped[str] = mapped_column(String(200), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    claim: Mapped[Claim] = relationship(back_populates="evidence_references")


class Uncertainty(Base):
    __tablename__ = "uncertainties"
    __table_args__ = (CheckConstraint("kind IN ('MISSING_CONTEXT', 'ALTERNATIVE_EXPLANATION', 'LIMITED_OBSERVATION', 'OTHER')", name="ck_uncertainty_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    claim: Mapped[Claim] = relationship(back_populates="uncertainties")


class UserConfirmation(Base):
    __tablename__ = "user_confirmations"
    __table_args__ = (
        UniqueConstraint("claim_id", name="uq_user_confirmation_claim"),
        CheckConstraint("decision IN ('CONFIRMED', 'REJECTED')", name="ck_confirmation_decision"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    claim: Mapped[Claim] = relationship(back_populates="confirmations")


class MemoryCandidate(Base):
    __tablename__ = "memory_candidates"
    __table_args__ = (
        UniqueConstraint("claim_id", name="uq_memory_candidates_claim_id"),
        CheckConstraint("source_type IN ('CLAIM', 'MANUAL')", name="ck_memory_candidate_source_type"),
        CheckConstraint(
            "(source_type = 'CLAIM' AND claim_id IS NOT NULL AND source_episode_updated_at IS NOT NULL) OR "
            "(source_type = 'MANUAL' AND claim_id IS NULL AND source_episode_updated_at IS NULL)",
            name="ck_memory_candidate_source_fields",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), index=True)
    claim_id: Mapped[int | None] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="CLAIM")
    claim_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evidence_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    uncertainty_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    model_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_episode_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pet: Mapped[Pet] = relationship(back_populates="memory_candidates")
    claim: Mapped[Claim | None] = relationship(back_populates="memory_candidate")
    decisions: Mapped[list["MemoryDecision"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", order_by="MemoryDecision.id"
    )

    @property
    def is_stale(self) -> bool:
        if self.source_type == "MANUAL":
            return False
        if self.claim is None or self.source_episode_updated_at is None:
            return True
        source = self.source_episode_updated_at
        current = self.claim.analysis_run.episode.updated_at
        if source.tzinfo is None:
            source = source.replace(tzinfo=timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return current > source

    @property
    def state(self) -> str:
        if self.is_stale:
            return "STALE"
        if not self.decisions:
            return "ELIGIBLE"
        return "ACTIVE" if self.decisions[-1].decision == "INCLUDE" else "WITHDRAWN"


class MemoryDecision(Base):
    __tablename__ = "memory_decisions"
    __table_args__ = (
        UniqueConstraint("candidate_id", "request_id", name="uq_memory_decision_candidate_request"),
        CheckConstraint("decision IN ('INCLUDE', 'WITHDRAW')", name="ck_memory_decision_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("memory_candidates.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped[MemoryCandidate] = relationship(back_populates="decisions")


class BaselineSnapshot(Base):
    __tablename__ = "baseline_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "pet_id", "window", "as_of", "algorithm_version", "source_fingerprint",
            name="uq_baseline_snapshot_identity",
        ),
        CheckConstraint("window IN ('7d', '30d', '90d', 'all')", name="ck_baseline_snapshot_window"),
        CheckConstraint(
            "status IN ('READY', 'INSUFFICIENT_DATA', 'EMPTY')",
            name="ck_baseline_snapshot_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), index=True)
    window: Mapped[str] = mapped_column(String(10), nullable=False)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(100), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pet: Mapped[Pet] = relationship(back_populates="baseline_snapshots")
    evidences: Mapped[list["BaselineEvidence"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan", order_by="BaselineEvidence.id"
    )
    _is_stale: ClassVar[bool] = False

    @property
    def is_stale(self) -> bool:
        return self._is_stale


class BaselineEvidence(Base):
    __tablename__ = "baseline_evidences"
    __table_args__ = (
        CheckConstraint("source_type IN ('EPISODE', 'OBSERVATION')", name="ck_baseline_evidence_source_type"),
        CheckConstraint("window_segment IN ('CURRENT', 'COMPARISON')", name="ck_baseline_evidence_segment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("baseline_snapshots.id", ondelete="CASCADE"), index=True)
    episode_id: Mapped[int | None] = mapped_column(ForeignKey("episodes.id", ondelete="SET NULL"), index=True)
    observation_id: Mapped[int | None] = mapped_column(ForeignKey("observations.id", ondelete="SET NULL"), index=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    window_segment: Mapped[str] = mapped_column(String(20), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(300), nullable=False)
    field_path: Mapped[str] = mapped_column(String(200), nullable=False)
    value_snapshot: Mapped[Any] = mapped_column(JSON, nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    snapshot: Mapped[BaselineSnapshot] = relationship(back_populates="evidences")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    actor_pseudonym: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_pseudonym: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
