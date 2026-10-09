from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_episode
from app.api.errors import APIError
from app.db.session import get_db
from app.schemas.analysis import AnalysisRunCreate, AnalysisRunRead, ConfirmationCreate, ConfirmationRead
from app.services.understanding import (
    AnalysisExecutionError,
    confirm_claim,
    execute_analysis,
    get_analysis_run,
    list_episode_analysis_runs,
)
from app.services.understanding_adapter import TextUnderstandingAdapter, get_text_understanding_adapter

router = APIRouter(tags=["text-understanding"])


@router.post("/episodes/{episode_id}/analysis-runs", response_model=AnalysisRunRead, status_code=201)
def create_analysis_run(
    episode_id: int,
    payload: AnalysisRunCreate,
    db: Session = Depends(get_db),
    adapter: TextUnderstandingAdapter = Depends(get_text_understanding_adapter),
):
    try:
        run = execute_analysis(db, episode_id, payload, adapter)
        db.commit()
        return run
    except AnalysisExecutionError as exc:
        db.commit()
        raise APIError(exc.status_code, exc.code, exc.message)
    except Exception:
        db.rollback()
        raise


@router.get("/episodes/{episode_id}/analysis-runs", response_model=list[AnalysisRunRead])
def list_analysis_runs(episode_id: int, db: Session = Depends(get_db)):
    require_episode(db, episode_id)
    return list_episode_analysis_runs(db, episode_id)


@router.get("/analysis-runs/{run_id}", response_model=AnalysisRunRead)
def read_analysis_run(run_id: int, db: Session = Depends(get_db)):
    run = get_analysis_run(db, run_id)
    if run is None:
        raise APIError(404, "ANALYSIS_RUN_NOT_FOUND", "Analysis run not found")
    return run


@router.post("/claims/{claim_id}/confirmations", response_model=ConfirmationRead, status_code=201)
def create_confirmation(claim_id: int, payload: ConfirmationCreate, db: Session = Depends(get_db)):
    try:
        confirmation = confirm_claim(db, claim_id, payload)
        db.commit()
        db.refresh(confirmation)
        return confirmation
    except IntegrityError:
        db.rollback()
        raise APIError(409, "CLAIM_ALREADY_DECIDED", "Claim already has a final user decision")
    except Exception:
        db.rollback()
        raise
