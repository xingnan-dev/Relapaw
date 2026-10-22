from datetime import UTC

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_csrf, require_current_user, require_episode, require_escalation, require_life_event, require_pet, require_plan
from app.api.errors import APIError
from app.db.session import get_db
from app.models import LifeEvent, ObservationPlan, ObservationPlanItem, PetBaseline, User, VeterinaryEscalation
from app.schemas.resources import (
    LifeEventCreate, LifeEventUpdate,
    LifeEventRead,
    ObservationPlanCreate,
    ObservationPlanRead,
    ObservationPlanUpdate,
    PetBaselineRead,
    PetBaselineUpsert,
    VeterinaryEscalationCreate,
    VeterinaryEscalationRead,
    VeterinaryEscalationUpdate,
)

router = APIRouter(tags=["longitudinal-memory"])


def _comparable_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@router.get("/pets/{pet_id}/baseline", response_model=PetBaselineRead)
def get_baseline(pet_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    require_pet(db, pet_id, user)
    baseline = db.scalar(select(PetBaseline).where(PetBaseline.pet_id == pet_id))
    if baseline is None:
        raise APIError(404, "PET_BASELINE_NOT_FOUND", "Pet baseline not found")
    return baseline


@router.put("/pets/{pet_id}/baseline", response_model=PetBaselineRead)
def upsert_baseline(pet_id: int, payload: PetBaselineUpsert, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    require_pet(db, pet_id, user, for_update=True)
    baseline = db.scalar(select(PetBaseline).where(PetBaseline.pet_id == pet_id))
    if baseline is None:
        baseline = PetBaseline(pet_id=pet_id, **payload.model_dump())
        db.add(baseline)
    else:
        for key, value in payload.model_dump().items():
            setattr(baseline, key, value)
    db.commit()
    db.refresh(baseline)
    return baseline


@router.get("/pets/{pet_id}/life-events", response_model=list[LifeEventRead])
def list_life_events(pet_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    require_pet(db, pet_id, user)
    return list(db.scalars(select(LifeEvent).where(LifeEvent.pet_id == pet_id).order_by(LifeEvent.happened_at.desc(), LifeEvent.id.desc())).all())


@router.post("/pets/{pet_id}/life-events", response_model=LifeEventRead, status_code=201)
def create_life_event(pet_id: int, payload: LifeEventCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    require_pet(db, pet_id, user, for_update=True)
    event = LifeEvent(pet_id=pet_id, **payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.patch("/life-events/{event_id}", response_model=LifeEventRead)
def update_life_event(event_id: int, payload: LifeEventUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    event = require_life_event(db, event_id, user, for_update=True)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return event


@router.get("/pets/{pet_id}/observation-plans", response_model=list[ObservationPlanRead])
def list_observation_plans(pet_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    require_pet(db, pet_id, user)
    return list(db.scalars(select(ObservationPlan).where(ObservationPlan.pet_id == pet_id).options(joinedload(ObservationPlan.items)).order_by(ObservationPlan.id.desc())).unique().all())


@router.get("/observation-plans/{plan_id}", response_model=ObservationPlanRead)
def get_observation_plan(plan_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    require_plan(db, plan_id, user)
    plan = db.scalar(select(ObservationPlan).where(ObservationPlan.id == plan_id).options(joinedload(ObservationPlan.items)))
    if plan is None:
        raise APIError(404, "OBSERVATION_PLAN_NOT_FOUND", "Observation plan not found")
    return plan


@router.post("/pets/{pet_id}/observation-plans", response_model=ObservationPlanRead, status_code=201)
def create_observation_plan(pet_id: int, payload: ObservationPlanCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    require_pet(db, pet_id, user, for_update=True)
    data = payload.model_dump(exclude={"items"})
    plan = ObservationPlan(pet_id=pet_id, **data)
    db.add(plan)
    db.flush()
    normalized_items = payload.items or [
        {"label": str(item.get("label", "")).strip(), "description": item.get("description"), "is_required": item.get("is_required", True)}
        for item in payload.items_to_observe if str(item.get("label", "")).strip()
    ]
    plan.items = [ObservationPlanItem(plan_id=plan.id, sort_order=index, **(item.model_dump() if hasattr(item, "model_dump") else item)) for index, item in enumerate(normalized_items)]
    db.commit()
    db.refresh(plan)
    return plan


@router.patch("/observation-plans/{plan_id}", response_model=ObservationPlanRead)
def update_observation_plan(plan_id: int, payload: ObservationPlanUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    plan = require_plan(db, plan_id, user, for_update=True)
    data = payload.model_dump(exclude_unset=True, exclude={"items"})
    if plan.status in {"COMPLETED", "CANCELLED"}:
        raise APIError(409, "OBSERVATION_PLAN_TERMINAL", "Completed or cancelled plans cannot be changed")
    next_status = data.get("status")
    allowed = {"DRAFT": {"ACTIVE", "CANCELLED"}, "ACTIVE": {"COMPLETED", "CANCELLED"}}
    if next_status is not None and next_status.value not in allowed.get(plan.status, set()):
        raise APIError(409, "INVALID_OBSERVATION_PLAN_TRANSITION", "Invalid observation plan status transition")
    effective_start = data.get("start_at", plan.start_at)
    effective_end = data.get("end_at", plan.end_at)
    comparable_start = _comparable_utc(effective_start)
    comparable_end = _comparable_utc(effective_end)
    if comparable_start and comparable_end and comparable_end < comparable_start:
        raise APIError(422, "INVALID_PLAN_DATES", "end_at must be on or after start_at")
    for key, value in data.items():
        setattr(plan, key, value)
    if payload.items is not None:
        if not payload.items:
            raise APIError(422, "OBSERVATION_PLAN_ITEMS_REQUIRED", "At least one observation item is required")
        plan.items.clear()
        db.flush()
        plan.items = [ObservationPlanItem(plan_id=plan.id, sort_order=index, **item.model_dump()) for index, item in enumerate(payload.items)]
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/episodes/{episode_id}/veterinary-escalations", response_model=list[VeterinaryEscalationRead])
def list_veterinary_escalations(episode_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    require_episode(db, episode_id, user)
    return list(db.scalars(select(VeterinaryEscalation).where(VeterinaryEscalation.episode_id == episode_id).order_by(VeterinaryEscalation.id.desc())).all())


@router.post("/episodes/{episode_id}/veterinary-escalations", response_model=VeterinaryEscalationRead, status_code=201)
def create_veterinary_escalation(episode_id: int, payload: VeterinaryEscalationCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    require_episode(db, episode_id, user, for_update=True)
    if payload.status.value != "OPEN":
        raise APIError(409, "INVALID_VETERINARY_ESCALATION_TRANSITION", "Veterinary escalation must be created as OPEN")
    escalation = VeterinaryEscalation(episode_id=episode_id, **payload.model_dump(mode="json"))
    db.add(escalation)
    db.commit()
    db.refresh(escalation)
    return escalation


@router.patch("/veterinary-escalations/{escalation_id}", response_model=VeterinaryEscalationRead)
def update_veterinary_escalation(escalation_id: int, payload: VeterinaryEscalationUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    escalation = require_escalation(db, escalation_id, user, for_update=True)
    data = payload.model_dump(exclude_unset=True, mode="json")
    if escalation.status == "CLOSED":
        raise APIError(409, "VETERINARY_ESCALATION_CLOSED", "Closed veterinary escalations cannot be changed")
    next_status = data.get("status")
    allowed = {
        "OPEN": {"SHARED_WITH_VET", "CLOSED"},
        "SHARED_WITH_VET": {"CLOSED"},
    }
    if next_status is not None and next_status not in allowed.get(escalation.status, set()):
        raise APIError(409, "INVALID_VETERINARY_ESCALATION_TRANSITION", "Invalid veterinary escalation status transition")
    for key, value in data.items():
        setattr(escalation, key, value)
    db.commit()
    db.refresh(escalation)
    return escalation
