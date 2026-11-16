from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_csrf, require_current_user, require_pet
from app.api.errors import APIError
from app.core.config import settings
from app.db.session import get_db
from app.models import MediaAttachment, User
from app.schemas.relationship import InteractionPatternCreate, InteractionPatternDecision, InteractionPatternRead, InteractionPatternUpdate, RelationshipEventCreate, RelationshipEventRead, RelationshipEventUpdate
from app.services.media_records import media_paths_for_record
from app.services.media_storage import cleanup_path
from app.services.relationships import RelationshipError, create_interaction_pattern, create_relationship_event, decide_interaction_pattern, delete_interaction_pattern, get_relationship_event, list_interaction_patterns, list_relationship_events, update_interaction_pattern, update_relationship_event

router = APIRouter(tags=["relationships"])


def _raise(exc: RelationshipError):
    raise APIError(exc.status_code, exc.code, exc.message)


@router.get("/pets/{pet_id}/relationship-events", response_model=list[RelationshipEventRead])
def read_relationship_events(pet_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    require_pet(db, pet_id, user)
    return list_relationship_events(db, pet_id, user)


@router.post("/relationship-events", response_model=RelationshipEventRead, status_code=201)
def create_event(payload: RelationshipEventCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    try:
        event = create_relationship_event(db, user, payload); db.commit(); return event
    except RelationshipError as exc:
        db.rollback(); _raise(exc)
    except IntegrityError:
        db.rollback(); raise APIError(409, "RELATIONSHIP_EVENT_CONFLICT", "The relationship event conflicted with another request")


@router.put("/relationship-events/{event_id}", response_model=RelationshipEventRead)
def update_event(event_id: int, payload: RelationshipEventUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    try:
        event = update_relationship_event(db, event_id, user, payload); db.commit(); return event
    except RelationshipError as exc:
        db.rollback(); _raise(exc)
    except IntegrityError:
        db.rollback(); raise APIError(409, "RELATIONSHIP_EVENT_CONFLICT", "The relationship event conflicted with another request")


@router.delete("/relationship-events/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    event = get_relationship_event(db, event_id, user, for_update=True)
    if event is None: raise APIError(404, "RELATIONSHIP_EVENT_NOT_FOUND", "Relationship event not found")
    paths = media_paths_for_record(db, settings.media_dir, MediaAttachment.relationship_event_id, event.id)
    try:
        db.delete(event); db.commit()
    except Exception:
        db.rollback(); raise
    for path in paths: cleanup_path(path, settings.media_dir)


@router.get("/pets/{pet_id}/interaction-patterns", response_model=list[InteractionPatternRead])
def read_interaction_patterns(pet_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    try:
        return list_interaction_patterns(db, pet_id, user)
    except RelationshipError as exc:
        _raise(exc)


@router.post("/interaction-patterns", response_model=InteractionPatternRead, status_code=201)
def create_pattern(payload: InteractionPatternCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    try:
        result = create_interaction_pattern(db, user, payload); db.commit(); return result
    except RelationshipError as exc:
        db.rollback(); _raise(exc)
    except IntegrityError:
        db.rollback(); raise APIError(409, "INTERACTION_PATTERN_CONFLICT", "The interaction pattern conflicted with another request")


@router.put("/interaction-patterns/{candidate_id}", response_model=InteractionPatternRead)
def update_pattern(candidate_id: int, payload: InteractionPatternUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    try:
        result = update_interaction_pattern(db, candidate_id, user, payload); db.commit(); return result
    except RelationshipError as exc:
        db.rollback(); _raise(exc)
    except IntegrityError:
        db.rollback(); raise APIError(409, "INTERACTION_PATTERN_CONFLICT", "The interaction pattern conflicted with another request")


@router.post("/interaction-patterns/{candidate_id}/decisions", response_model=InteractionPatternRead)
def decide_pattern(candidate_id: int, payload: InteractionPatternDecision, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    try:
        result = decide_interaction_pattern(db, candidate_id, user, payload); db.commit(); return result
    except RelationshipError as exc:
        db.rollback(); _raise(exc)
    except IntegrityError:
        db.rollback(); raise APIError(409, "INTERACTION_PATTERN_CONFLICT", "The interaction pattern conflicted with another request")


@router.delete("/interaction-patterns/{candidate_id}", status_code=204)
def delete_pattern(candidate_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    try:
        delete_interaction_pattern(db, candidate_id, user); db.commit()
    except RelationshipError as exc:
        db.rollback(); _raise(exc)
    except IntegrityError:
        db.rollback(); raise APIError(409, "INTERACTION_PATTERN_CONFLICT", "The interaction pattern conflicted with another request")
