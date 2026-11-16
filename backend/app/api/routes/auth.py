from datetime import UTC, datetime
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, require_auth_context, require_csrf
from app.api.errors import APIError
from app.core.config import settings
from app.db.session import get_db
from app.models import IdentityInvitation, TermsAcceptance, User, UserIdentity, UserSession
from app.schemas.auth import ChallengeRequest, ChallengeVerify, CsrfRead, SessionRead
from app.services.identity import (
    IdentityDeliveryError,
    IdentityRateLimitError,
    IdentityVerificationError,
    build_identity_adapter,
)
from app.services.sessions import create_session, get_or_create_user, token_digest

router = APIRouter(prefix="/auth", tags=["auth"])
identity_adapter = build_identity_adapter(settings)


def _request_source(request: Request) -> str:
    # Deliberately use the direct peer. Forwarded headers are untrusted until a
    # reviewed proxy configuration supplies a trusted client-address boundary.
    return request.client.host if request.client is not None else "unknown"


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


def _require_valid_locked_invitation(
    invitation: IdentityInvitation | None, now: datetime
) -> IdentityInvitation:
    if invitation is None or invitation.status not in {"PENDING", "ACCEPTED"}:
        raise APIError(401, "CHALLENGE_INVALID", "Challenge verification failed")
    invitation_expiry = invitation.expires_at
    if invitation_expiry is not None and invitation_expiry.tzinfo is None:
        invitation_expiry = invitation_expiry.replace(tzinfo=UTC)
    if invitation.status == "PENDING" and invitation_expiry is not None and invitation_expiry <= now:
        raise APIError(401, "CHALLENGE_INVALID", "Challenge verification failed")
    return invitation


@router.post("/otp/request", status_code=202)
def request_challenge(payload: ChallengeRequest, request: Request, db: Session = Depends(get_db)):
    if request.headers.get("origin") not in settings.cors_origins:
        raise APIError(403, "ORIGIN_FORBIDDEN", "Request origin is not allowed")
    # Origin validation is intentionally identical for known and unknown addresses.
    try:
        identity_adapter.request_challenge(payload.email, db=db, source=_request_source(request))
    except IdentityRateLimitError as exc:
        raise APIError(429, "OTP_RATE_LIMITED", "Please wait before requesting another code") from exc
    except IdentityDeliveryError as exc:
        raise APIError(503, "OTP_DELIVERY_UNAVAILABLE", "The code could not be sent; please try again") from exc
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
        identity = identity_adapter.verify_challenge(
            payload.email, payload.code, db=db, source=_request_source(request)
        )
    except IdentityRateLimitError as exc:
        raise APIError(429, "OTP_RATE_LIMITED", "Please wait before trying again") from exc
    except IdentityVerificationError as exc:
        raise APIError(401, "CHALLENGE_INVALID", "Challenge verification failed") from exc
    invitation = db.scalar(select(IdentityInvitation).where(
        IdentityInvitation.provider == identity.provider,
        IdentityInvitation.subject == identity.subject,
        IdentityInvitation.status.in_(["PENDING", "ACCEPTED"]),
    ))
    if invitation is None:
        raise APIError(401, "CHALLENGE_INVALID", "Challenge verification failed")

    known_user_id = invitation.accepted_user_id or db.scalar(select(UserIdentity.user_id).where(
        UserIdentity.provider == identity.provider,
        UserIdentity.subject == identity.subject,
    ))
    user = None
    if known_user_id is not None:
        # Account deletion/purge also starts with the User row. Keep returning-login
        # lock order User -> Invitation so FK cleanup cannot deadlock with login.
        user = db.scalar(
            select(User).where(User.id == known_user_id).with_for_update().execution_options(populate_existing=True)
        )
        invitation = db.scalar(
            select(IdentityInvitation)
            .where(IdentityInvitation.id == invitation.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    else:
        invitation = db.scalar(
            select(IdentityInvitation)
            .where(IdentityInvitation.id == invitation.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        # A concurrent first login may have accepted the invitation while this
        # request waited. Release the invitation lock and restart in User-first order.
        known_user_id = invitation.accepted_user_id if invitation is not None else None
        if known_user_id is None:
            known_user_id = db.scalar(select(UserIdentity.user_id).where(
                UserIdentity.provider == identity.provider,
                UserIdentity.subject == identity.subject,
            ))
        if known_user_id is not None:
            invitation_id = invitation.id if invitation is not None else None
            db.rollback()
            user = db.scalar(
                select(User).where(User.id == known_user_id).with_for_update().execution_options(populate_existing=True)
            )
            invitation = db.scalar(
                select(IdentityInvitation)
                .where(IdentityInvitation.id == invitation_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
    now = datetime.now(UTC)
    invitation = _require_valid_locked_invitation(invitation, now)
    if user is None:
        user = get_or_create_user(db, identity)
        db.flush()
        user = db.scalar(
            select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True)
        )
    if user is None:
        raise APIError(401, "CHALLENGE_INVALID", "Challenge verification failed")
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
    return SessionRead(user_id=user.id, status=user.status, consent_required=_consent_required(db, user.id), onboarding_complete=user.onboarding_completed_at is not None)


@router.get("/session", response_model=SessionRead)
def read_session(response: Response, context: AuthContext = Depends(require_auth_context), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return SessionRead(user_id=context.user.id, status=context.user.status, consent_required=_consent_required(db, context.user.id), onboarding_complete=context.user.onboarding_completed_at is not None)


@router.post("/onboarding/complete", response_model=SessionRead)
def complete_onboarding(
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    if _consent_required(db, context.user.id):
        raise APIError(403, "CONSENT_REQUIRED", "Current Terms and Privacy Notice must be accepted")
    user = db.scalar(select(User).where(User.id == context.user.id).with_for_update())
    if user is None or user.status != "ACTIVE":
        raise APIError(401, "SESSION_INVALID", "Session is invalid or expired")
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = datetime.now(UTC)
        db.commit()
    return SessionRead(user_id=user.id, status=user.status, consent_required=False, onboarding_complete=True)


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
