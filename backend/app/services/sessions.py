from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import new as hmac_new
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import User, UserIdentity, UserSession
from app.services.identity import VerifiedIdentity


def utc_now() -> datetime:
    return datetime.now(UTC)


def token_digest(value: str, settings: Settings) -> str:
    return hmac_new(
        settings.session_pepper.get_secret_value().encode(), value.encode(), sha256
    ).hexdigest()


def get_or_create_user(db: Session, identity: VerifiedIdentity) -> User:
    mapping = db.scalar(select(UserIdentity).where(
        UserIdentity.provider == identity.provider,
        UserIdentity.subject == identity.subject,
    ))
    now = utc_now()
    if mapping is not None:
        mapping.last_verified_at = now
        return mapping.user
    user = User(status="ACTIVE")
    db.add(user)
    db.flush()
    db.add(UserIdentity(
        user_id=user.id,
        provider=identity.provider,
        subject=identity.subject,
        last_verified_at=now,
    ))
    return user


def create_session(
    db: Session, user: User, settings: Settings, user_agent: str | None
) -> tuple[UserSession, str, str]:
    now = utc_now()
    raw_token = token_urlsafe(32)
    raw_csrf = token_urlsafe(32)
    session = UserSession(
        user_id=user.id,
        token_hash=token_digest(raw_token, settings),
        csrf_token_hash=token_digest(raw_csrf, settings),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(days=settings.session_absolute_days),
        user_agent_summary=(user_agent or "")[:200] or None,
    )
    user.last_login_at = now
    db.add(session)
    db.flush()
    return session, raw_token, raw_csrf
