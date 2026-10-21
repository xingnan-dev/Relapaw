from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_analysis_run, require_claim, require_csrf, require_current_user, require_episode
from app.api.errors import APIError
from app.api.routes.capabilities import get_ai_block_reason, get_ai_enabled
from app.db.session import get_db
from app.domain.enums import SafetyStatus
from app.models import AnalysisRun, User
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
    ai_enabled: bool = Depends(get_ai_enabled),
    ai_block_reason: str | None = Depends(get_ai_block_reason),
    user: User = Depends(require_current_user),
    _csrf=Depends(require_csrf),
):
    episode = require_episode(db, episode_id, user)
    safety_result = episode.safety_check.result if episode.safety_check is not None else None
    if safety_result == SafetyStatus.NORMAL and not ai_enabled:
        if ai_block_reason == "MODEL_NOT_QUALIFIED":
            raise APIError(403, "MODEL_NOT_QUALIFIED", "Text Understanding model has not passed qualification")
        raise APIError(403, "FEATURE_DISABLED", "Text Understanding is disabled for this release")
    try:
        run = execute_analysis(db, episode_id, payload, adapter)
        db.commit()
        return run
    except AnalysisExecutionError as exc:
        db.commit()
        raise APIError(exc.status_code, exc.code, exc.message)
    except Exception:
        db.rollback()
        # The RUNNING row is a durable remote-call reservation. If local result
        # persistence fails unexpectedly, remove only that unfinished aggregate
        # so retries are possible and no permanent phantom run remains.
        db.query(AnalysisRun).filter(
            AnalysisRun.episode_id == episode_id,
            AnalysisRun.request_id == payload.request_id,
            AnalysisRun.status == "RUNNING",
        ).delete(synchronize_session=False)
        db.commit()
        raise


@router.get("/episodes/{episode_id}/analysis-runs", response_model=list[AnalysisRunRead])
def list_analysis_runs(episode_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    require_episode(db, episode_id, user)
    return list_episode_analysis_runs(db, episode_id)


@router.get("/analysis-runs/{run_id}", response_model=AnalysisRunRead)
def read_analysis_run(run_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    require_analysis_run(db, run_id, user)
    run = get_analysis_run(db, run_id)
    if run is None:
        raise APIError(404, "ANALYSIS_RUN_NOT_FOUND", "Analysis run not found")
    return run


@router.post("/claims/{claim_id}/confirmations", response_model=ConfirmationRead, status_code=201)
def create_confirmation(claim_id: int, payload: ConfirmationCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    require_claim(db, claim_id, user)
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
