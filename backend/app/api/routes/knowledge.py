from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_current_user, require_episode
from app.api.errors import APIError
from app.db.session import get_db
from app.domain.educational_knowledge import KNOWLEDGE_SET
from app.models import User
from app.schemas.knowledge import EducationalGuidanceRead, KnowledgeSetRead

router = APIRouter(tags=["educational-knowledge"])


@router.get("/knowledge", response_model=KnowledgeSetRead)
def list_knowledge(_user: User = Depends(require_current_user)):
    return KNOWLEDGE_SET


@router.get("/episodes/{episode_id}/educational-guidance", response_model=EducationalGuidanceRead)
def get_educational_guidance(episode_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    episode = require_episode(db, episode_id, user)
    if episode.safety_check is None or episode.safety_check.result != "NORMAL":
        raise APIError(409, "EDUCATION_BLOCKED_BY_SAFETY", "Educational guidance is unavailable until the current safety result is NORMAL")
    species = episode.pet.species.strip().lower()
    known_species = {value for entry in KNOWLEDGE_SET["entries"] for value in entry["species"] if value != "other"}
    match_species = species if species in known_species else "other"
    entries = [entry for entry in KNOWLEDGE_SET["entries"] if match_species in entry["species"]]
    facts = [f"Observation: {item.description}" for item in episode.observations]
    for label, value in (("Time", episode.happened_at.isoformat()), ("Location", episode.location), ("Duration seconds", episode.duration_seconds), ("Frequency", episode.frequency_count)):
        if value is not None:
            facts.append(f"{label}: {value}")
    return {
        "status": "EDUCATIONAL_ONLY",
        "knowledge_version": KNOWLEDGE_SET["version"],
        "review_status": KNOWLEDGE_SET["review_status"],
        "review_note": KNOWLEDGE_SET["review_note"],
        "fact_summary": facts,
        "entries": entries,
        "limitations": ["Uses only recorded facts and the cited local example set.", "Does not diagnose, treat, recommend medication or provide dosage.", "Does not change observations, baselines or memories."],
    }
