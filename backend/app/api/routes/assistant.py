from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_csrf, require_current_user, require_episode
from app.api.errors import APIError
from app.api.routes.capabilities import get_ai_block_reason, get_ai_enabled
from app.db.session import get_db
from app.models import User
from app.schemas.assistant import AssistantGuidanceRunRead, GuidanceRunCreate
from app.services.assistant_adapter import AssistantGuidanceAdapter, get_assistant_guidance_adapter
from app.services.assistant_guidance import GuidanceExecutionError, execute_guidance, list_guidance_runs

router = APIRouter(tags=["assistant-guidance"])


@router.post("/episodes/{episode_id}/assistant-guidance-runs", response_model=AssistantGuidanceRunRead, status_code=201)
def create_guidance_run(
    episode_id: int,
    payload: GuidanceRunCreate,
    db: Session = Depends(get_db),
    ai_enabled: bool = Depends(get_ai_enabled),
    ai_block_reason: str | None = Depends(get_ai_block_reason),
    adapter: AssistantGuidanceAdapter = Depends(get_assistant_guidance_adapter),
    user: User = Depends(require_current_user),
    _csrf=Depends(require_csrf),
):
    episode = require_episode(db, episode_id, user)
    safety_normal = episode.safety_check is not None and episode.safety_check.result == "NORMAL"
    if safety_normal and not ai_enabled:
        if ai_block_reason:
            raise APIError(403, "MODEL_NOT_QUALIFIED", "Assistant model has not passed qualification")
        raise APIError(403, "FEATURE_DISABLED", "Assistant guidance is disabled for this release")
    try:
        run = execute_guidance(db, episode, payload, adapter)
        db.commit()
        return run
    except GuidanceExecutionError as exc:
        db.commit()
        raise APIError(exc.status_code, exc.code, exc.message)
    except Exception:
        db.rollback()
        raise


@router.get("/episodes/{episode_id}/assistant-guidance-runs", response_model=list[AssistantGuidanceRunRead])
def read_guidance_runs(episode_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    require_episode(db, episode_id, user)
    return list_guidance_runs(db, episode_id)
