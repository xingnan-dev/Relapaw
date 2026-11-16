"""Create a hashed invitation for the local identity adapter.

This utility is intentionally unavailable in staging and production. A reviewed
production adapter must own invitation delivery and verification there.
"""
import argparse
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.api.routes.auth import identity_adapter
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import IdentityInvitation


def invite_local_email(email: str, *, valid_days: int = 7) -> IdentityInvitation:
    if settings.environment not in {"development", "test", "demo"}:
        raise RuntimeError("Local invitations are forbidden in staging and production")
    subject = identity_adapter.subject_for(email)
    if subject is None:
        raise ValueError("A valid email address is required")
    with SessionLocal() as db:
        invitation = db.scalar(select(IdentityInvitation).where(
            IdentityInvitation.provider == "local-invite",
            IdentityInvitation.subject == subject,
        ))
        if invitation is None:
            invitation = IdentityInvitation(
                provider="local-invite", subject=subject, status="PENDING",
                expires_at=datetime.now(UTC) + timedelta(days=valid_days),
            )
            db.add(invitation)
        elif invitation.status != "ACCEPTED":
            invitation.status = "PENDING"
            invitation.expires_at = datetime.now(UTC) + timedelta(days=valid_days)
        db.commit()
        db.refresh(invitation)
        return invitation


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local-only hashed Beta invitation")
    parser.add_argument("email")
    parser.add_argument("--valid-days", type=int, default=7, choices=range(1, 31))
    args = parser.parse_args()
    invitation = invite_local_email(args.email, valid_days=args.valid_days)
    print(f"local invitation ready: id={invitation.id}, status={invitation.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
