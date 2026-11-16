from datetime import UTC, datetime
from hashlib import sha256
from hmac import new as hmac_new
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import AuditEvent


def pseudonym(value: str | int, settings: Settings) -> str:
    return hmac_new(
        settings.session_pepper.get_secret_value().encode(), str(value).encode(), sha256
    ).hexdigest()


def append_audit_event(
    db: Session, settings: Settings, *, actor_user_id: str, event_type: str,
    subject_type: str, subject_id: str | int, metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_pseudonym=pseudonym(actor_user_id, settings),
        event_type=event_type,
        subject_type=subject_type,
        subject_pseudonym=pseudonym(subject_id, settings),
        metadata_json=metadata or {},
        created_at=datetime.now(UTC),
    )
    db.add(event)
    return event
