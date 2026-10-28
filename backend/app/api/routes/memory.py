from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_claim, require_csrf, require_current_user, require_memory_candidate, require_pet
from app.api.errors import APIError
from app.db.session import get_db
from app.models import MediaAttachment, MemoryCandidateMediaReference, User
from app.schemas.memory import ManualMemoryCreate, ManualMemoryUpdate, MemoryCandidateRead, MemoryDecisionCreate, MemoryMediaReferenceCreate
from app.services.memory import (
    MemoryError,
    append_memory_decision,
    create_manual_memory_candidate,
    get_memory_candidate_by_claim,
    list_long_term_memory,
    list_memory_candidates,
    materialize_memory_candidate,
    update_manual_memory_candidate,
)

router = APIRouter(tags=["long-term-memory"])


def _raise_memory_error(exc: MemoryError):
    raise APIError(exc.status_code, exc.code, exc.message)


@router.post("/claims/{claim_id}/memory-candidate", response_model=MemoryCandidateRead, status_code=201)
def create_memory_candidate(claim_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    require_claim(db, claim_id, user)
    try:
        candidate = materialize_memory_candidate(db, claim_id)
        db.commit()
        return candidate
    except MemoryError as exc:
        db.rollback()
        _raise_memory_error(exc)
    except IntegrityError:
        db.rollback()
        existing = get_memory_candidate_by_claim(db, claim_id)
        if existing is None:
            raise APIError(409, "MEMORY_CANDIDATE_CONFLICT", "The memory candidate conflicted with another request")
        return existing


@router.post("/pets/{pet_id}/memory-candidates/manual", response_model=MemoryCandidateRead, status_code=201)
def create_manual_candidate(
    pet_id: int,
    payload: ManualMemoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_current_user),
    _csrf=Depends(require_csrf),
):
    require_pet(db, pet_id, user)
    candidate = create_manual_memory_candidate(db, pet_id, payload)
    db.commit()
    return candidate


@router.get("/pets/{pet_id}/memory-candidates", response_model=list[MemoryCandidateRead])
def read_memory_candidates(pet_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    require_pet(db, pet_id, user)
    return list_memory_candidates(db, pet_id)


@router.patch("/memory-candidates/{candidate_id}", response_model=MemoryCandidateRead)
def update_manual_candidate(candidate_id: int, payload: ManualMemoryUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    require_memory_candidate(db, candidate_id, user)
    try:
        candidate = update_manual_memory_candidate(db, candidate_id, payload)
        db.commit()
        return candidate
    except MemoryError as exc:
        db.rollback()
        _raise_memory_error(exc)
    except IntegrityError:
        db.rollback()
        raise APIError(409, "MEMORY_REVISION_CONFLICT", "The memory revision conflicted with another request")


@router.get("/pets/{pet_id}/long-term-memory", response_model=list[MemoryCandidateRead])
def read_long_term_memory(pet_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    require_pet(db, pet_id, user)
    return list_long_term_memory(db, pet_id)


@router.post("/memory-candidates/{candidate_id}/decisions", response_model=MemoryCandidateRead, status_code=201)
def create_memory_decision(candidate_id: int, payload: MemoryDecisionCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    require_memory_candidate(db, candidate_id, user)
    try:
        candidate = append_memory_decision(db, candidate_id, payload)
        db.commit()
        return candidate
    except MemoryError as exc:
        db.rollback()
        _raise_memory_error(exc)
    except IntegrityError:
        db.rollback()
        raise APIError(409, "MEMORY_DECISION_CONFLICT", "The memory decision conflicted with another request")


@router.post("/memory-candidates/{candidate_id}/media-references", response_model=MemoryCandidateRead, status_code=201)
def add_memory_media_reference(candidate_id: int, payload: MemoryMediaReferenceCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    candidate = require_memory_candidate(db, candidate_id, user)
    attachment = db.scalar(select(MediaAttachment).where(MediaAttachment.id == payload.media_attachment_id, MediaAttachment.pet_id == candidate.pet_id))
    if attachment is None: raise APIError(404, "MEDIA_NOT_FOUND", "Media attachment not found")
    if db.scalar(select(MemoryCandidateMediaReference.id).where(MemoryCandidateMediaReference.candidate_id == candidate.id, MemoryCandidateMediaReference.media_attachment_id == attachment.id)) is not None:
        raise APIError(409, "MEMORY_MEDIA_REFERENCE_EXISTS", "Media is already referenced by this candidate")
    db.add(MemoryCandidateMediaReference(candidate_id=candidate.id, media_attachment_id=attachment.id)); db.commit()
    return require_memory_candidate(db, candidate.id, user)


@router.delete("/memory-candidates/{candidate_id}/media-references/{attachment_id}", response_model=MemoryCandidateRead)
def remove_memory_media_reference(candidate_id: int, attachment_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    candidate = require_memory_candidate(db, candidate_id, user)
    reference = db.scalar(select(MemoryCandidateMediaReference).where(MemoryCandidateMediaReference.candidate_id == candidate.id, MemoryCandidateMediaReference.media_attachment_id == attachment_id))
    if reference is None: raise APIError(404, "MEMORY_MEDIA_REFERENCE_NOT_FOUND", "Media reference not found")
    db.delete(reference); db.commit(); return require_memory_candidate(db, candidate.id, user)
