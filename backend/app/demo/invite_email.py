"""Create a hashed invitation for the configured Resend email identity.

The command never reads or prints the Resend API key and does not send mail. Run it
from the backend directory after applying migrations and configuring backend/.env.
"""
import argparse
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.auth import identity_adapter
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import IdentityInvitation
from app.services.identity import DatabaseEmailOtpIdentityAdapter


def invite_email(
    email: str,
    *,
    valid_days: int = 7,
    session_factory: sessionmaker[Session] = SessionLocal,
    adapter=identity_adapter,
) -> IdentityInvitation:
    if not isinstance(adapter, DatabaseEmailOtpIdentityAdapter):
        raise RuntimeError("Resend email identity mode must be configured")
    subject = adapter.subject_for(email)
    if subject is None:
        raise ValueError("A valid email address is required")
    with session_factory() as db:
        invitation = db.scalar(select(IdentityInvitation).where(
            IdentityInvitation.provider == adapter.provider,
            IdentityInvitation.subject == subject,
        ))
        if invitation is None:
            invitation = IdentityInvitation(
                provider=adapter.provider,
                subject=subject,
                status="PENDING",
                expires_at=datetime.now(UTC) + timedelta(days=valid_days),
            )
            db.add(invitation)
        elif invitation.status == "REVOKED":
            raise RuntimeError("A revoked invitation requires an explicit administrative review")
        elif invitation.status == "PENDING":
            invitation.expires_at = datetime.now(UTC) + timedelta(days=valid_days)
        db.commit()
        db.refresh(invitation)
        return invitation


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a hashed Resend Beta invitation")
    parser.add_argument("--valid-days", type=int, default=7, choices=range(1, 31))
    args = parser.parse_args()
    email = settings.email_test_recipient
    if not email:
        email = input("Email to invite (input is not printed by Relapaw): ").strip()
    invitation = invite_email(email, valid_days=args.valid_days)
    print(f"email invitation ready: id={invitation.id}, status={invitation.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
