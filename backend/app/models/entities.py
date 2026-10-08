from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, String, Text, func
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pet: Mapped[Pet] = relationship(back_populates="episodes")
    observations: Mapped[list["Observation"]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    owner_interpretations: Mapped[list["OwnerInterpretation"]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    veterinary_escalations: Mapped[list["VeterinaryEscalation"]] = relationship(back_populates="episode", cascade="all, delete-orphan")


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    behavior_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    episode: Mapped[Episode] = relationship(back_populates="observations")


class OwnerInterpretation(Base):
    __tablename__ = "owner_interpretations"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    interpretation: Mapped[str] = mapped_column(Text, nullable=False)
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


class VeterinaryEscalation(Base):
    __tablename__ = "veterinary_escalations"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    vet_brief: Mapped[str | None] = mapped_column(Text)
    episode: Mapped[Episode] = relationship(back_populates="veterinary_escalations")

