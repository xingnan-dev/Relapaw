from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(primary_key=True)
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


class OwnerProfile(Base):
    __tablename__ = "owner_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
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
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    measured_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(50))
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
        CheckConstraint("status IN ('COMPLETED', 'FAILED', 'BLOCKED_BY_SAFETY')", name="ck_analysis_run_status"),
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
