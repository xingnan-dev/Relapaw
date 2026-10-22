from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_csrf, require_current_user, require_pet
from app.api.errors import APIError
from app.db.session import get_db
from app.models import User
from app.schemas.relationship import RelationshipEventCreate, RelationshipEventRead, RelationshipEventUpdate
from app.services.relationships import RelationshipError, create_relationship_event, list_relationship_events, update_relationship_event

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
