from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_pet
from app.api.errors import APIError
from app.db.session import get_db
from app.domain.enums import BaselineWindow
from app.schemas.baseline import BaselineRecompute, BaselineSnapshotRead
from app.services.baseline import get_latest_snapshot, get_snapshot, recompute_snapshot

router = APIRouter(tags=["quantitative-baselines"])


@router.post("/pets/{pet_id}/baseline-snapshots/recompute", response_model=BaselineSnapshotRead, status_code=201)
def recompute_baseline(pet_id: int, payload: BaselineRecompute, db: Session = Depends(get_db)):
    require_pet(db, pet_id)
    try:
        snapshot = recompute_snapshot(db, pet_id, payload.window.value, payload.as_of)
        db.commit()
        return snapshot
    except IntegrityError:
        db.rollback()
        snapshot = recompute_snapshot(db, pet_id, payload.window.value, payload.as_of)
        db.commit()
        return snapshot


@router.get("/pets/{pet_id}/baseline-snapshots/latest", response_model=BaselineSnapshotRead)
def read_latest_baseline(pet_id: int, window: BaselineWindow, db: Session = Depends(get_db)):
    require_pet(db, pet_id)
    snapshot = get_latest_snapshot(db, pet_id, window.value)
    if snapshot is None:
        raise APIError(404, "BASELINE_SNAPSHOT_NOT_FOUND", "Baseline snapshot not found")
    return snapshot


@router.get("/baseline-snapshots/{snapshot_id}", response_model=BaselineSnapshotRead)
def read_baseline(snapshot_id: int, db: Session = Depends(get_db)):
    snapshot = get_snapshot(db, snapshot_id)
    if snapshot is None:
        raise APIError(404, "BASELINE_SNAPSHOT_NOT_FOUND", "Baseline snapshot not found")
    return snapshot
