from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, require_auth_context, require_csrf, require_current_user
from app.api.errors import APIError
from app.core.config import settings
from app.db.session import get_db
from app.models import TermsAcceptance, User
from app.schemas.privacy import AccountDeletionRead, AccountDeletionRequest, ConsentCreate, PrivacyNoticeRead
from app.services.audit import append_audit_event
from app.services.privacy import build_account_export, request_account_deletion

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/notice", response_model=PrivacyNoticeRead)
def read_privacy_notice(_context: AuthContext = Depends(require_auth_context)):
    return PrivacyNoticeRead(
        terms_version=settings.terms_version,
        privacy_version=settings.privacy_version,
        legal_review_status="APPROVED" if settings.legal_documents_approved else "PENDING",
        data_inventory_version="relapaw-data-inventory/v1",
    )


@router.post("/consent", status_code=201)
def accept_consent(
    payload: ConsentCreate,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    if payload.terms_version != settings.terms_version or payload.privacy_version != settings.privacy_version:
        raise APIError(409, "POLICY_VERSION_CHANGED", "Policy versions changed; reload before accepting")
    if not payload.affirm_adult_owner:
        raise APIError(422, "ADULT_CONFIRMATION_REQUIRED", "Adult owner confirmation is required")
    existing = db.scalar(select(TermsAcceptance).where(
        TermsAcceptance.user_id == context.user.id,
        TermsAcceptance.terms_version == payload.terms_version,
        TermsAcceptance.privacy_version == payload.privacy_version,
    ))
    if existing is not None:
        return {"status": "accepted"}
    db.add(TermsAcceptance(
        user_id=context.user.id, terms_version=payload.terms_version,
        privacy_version=payload.privacy_version, accepted_at=datetime.now(UTC), source=payload.source,
    ))
    append_audit_event(db, settings, actor_user_id=context.user.id, event_type="POLICIES_ACCEPTED", subject_type="USER", subject_id=context.user.id, metadata={"terms_version": payload.terms_version, "privacy_version": payload.privacy_version})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        concurrent = db.scalar(select(TermsAcceptance).where(
            TermsAcceptance.user_id == context.user.id,
            TermsAcceptance.terms_version == payload.terms_version,
            TermsAcceptance.privacy_version == payload.privacy_version,
        ))
        if concurrent is None:
            raise
    return {"status": "accepted"}


@router.get("/export")
def export_account_data(
    user: User = Depends(require_current_user), db: Session = Depends(get_db),
):
    payload = build_account_export(db, user, settings)
    append_audit_event(db, settings, actor_user_id=user.id, event_type="ACCOUNT_DATA_EXPORTED", subject_type="USER", subject_id=user.id, metadata={"format": payload["format"]})
    db.commit()
    return JSONResponse(
        payload,
        headers={"Content-Disposition": "attachment; filename=relapaw-account-export.json", "Cache-Control": "no-store"},
    )


@router.delete("/account", response_model=AccountDeletionRead, status_code=202)
def delete_account(
    _payload: AccountDeletionRequest,
    response: Response,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User)
        .where(User.id == context.user.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None or user.status != "ACTIVE":
        raise APIError(409, "ACCOUNT_DELETION_ALREADY_REQUESTED", "Account deletion is already pending")
    due = request_account_deletion(db, user, settings)
    db.commit()
    response.delete_cookie(settings.session_cookie_name, secure=settings.secure_cookies, httponly=True, samesite="lax", path="/")
    return AccountDeletionRead(status="PENDING_DELETION", deletion_due_at=due)
