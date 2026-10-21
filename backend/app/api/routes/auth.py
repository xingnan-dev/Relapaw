from datetime import UTC, datetime
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, require_auth_context, require_csrf
from app.api.errors import APIError
from app.core.config import settings
from app.db.session import get_db
from app.models import IdentityInvitation, TermsAcceptance, UserSession
from app.schemas.auth import ChallengeRequest, ChallengeVerify, CsrfRead, SessionRead
from app.services.identity import IdentityVerificationError, LocalInviteIdentityAdapter
from app.services.sessions import create_session, get_or_create_user, token_digest

router = APIRouter(prefix="/auth", tags=["auth"])
identity_adapter = LocalInviteIdentityAdapter(settings)


def _consent_required(db: Session, user_id: str) -> bool:
    return db.scalar(select(TermsAcceptance.id).where(
        TermsAcceptance.user_id == user_id,
        TermsAcceptance.terms_version == settings.terms_version,
        TermsAcceptance.privacy_version == settings.privacy_version,
    )) is None


def _set_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        raw_token,
        max_age=settings.session_absolute_days * 86400,
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def _clear_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.post("/otp/request", status_code=202)
def request_challenge(payload: ChallengeRequest, request: Request):
    if request.headers.get("origin") not in settings.cors_origins:
        raise APIError(403, "ORIGIN_FORBIDDEN", "Request origin is not allowed")
    # Origin validation is intentionally identical for known and unknown addresses.
    identity_adapter.request_challenge(payload.email)
    return {"status": "challenge_requested"}


@router.post("/otp/verify", response_model=SessionRead)
def verify_challenge(
    payload: ChallengeVerify,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    if request.headers.get("origin") not in settings.cors_origins:
        raise APIError(403, "ORIGIN_FORBIDDEN", "Request origin is not allowed")
    try:
        identity = identity_adapter.verify_challenge(payload.email, payload.code)
    except IdentityVerificationError as exc:
        raise APIError(401, "CHALLENGE_INVALID", "Challenge verification failed") from exc
    invitation = db.scalar(select(IdentityInvitation).where(
        IdentityInvitation.provider == identity.provider,
        IdentityInvitation.subject == identity.subject,
        IdentityInvitation.status.in_(["PENDING", "ACCEPTED"]),
    ))
    now = datetime.now(UTC)
    invitation_expiry = invitation.expires_at if invitation is not None else None
    if invitation_expiry is not None and invitation_expiry.tzinfo is None:
        invitation_expiry = invitation_expiry.replace(tzinfo=UTC)
    if invitation is None or (invitation_expiry is not None and invitation_expiry <= now):
        raise APIError(401, "CHALLENGE_INVALID", "Challenge verification failed")
    user = get_or_create_user(db, identity)
    if user.status != "ACTIVE":
        raise APIError(401, "CHALLENGE_INVALID", "Challenge verification failed")
    # A successful login rotates all existing sessions for this identity.
    if invitation.status == "PENDING":
        invitation.status = "ACCEPTED"
        invitation.accepted_user_id = user.id
        invitation.accepted_at = now
    elif invitation.accepted_user_id != user.id:
        raise APIError(401, "CHALLENGE_INVALID", "Challenge verification failed")
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    _session, raw_token, _raw_csrf = create_session(db, user, settings, request.headers.get("user-agent"))
    db.commit()
    _set_cookie(response, raw_token)
    return SessionRead(user_id=user.id, status=user.status, consent_required=_consent_required(db, user.id))


@router.get("/session", response_model=SessionRead)
def read_session(response: Response, context: AuthContext = Depends(require_auth_context), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return SessionRead(user_id=context.user.id, status=context.user.status, consent_required=_consent_required(db, context.user.id))


@router.post("/csrf", response_model=CsrfRead)
def get_csrf(
    request: Request,
    response: Response,
    context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
):
    if request.headers.get("origin") not in settings.cors_origins:
        raise APIError(403, "ORIGIN_FORBIDDEN", "Request origin is not allowed")
    raw_token = token_urlsafe(32)
    context.session.csrf_token_hash = token_digest(raw_token, settings)
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return CsrfRead(csrf_token=raw_token)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    context.session.revoked_at = datetime.now(UTC)
    db.commit()
    _clear_cookie(response)
