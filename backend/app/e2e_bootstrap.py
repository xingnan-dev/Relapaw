"""Local Playwright-only bootstrap; refuses every database except the exact E2E file."""
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.api.routes.auth import identity_adapter
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import IdentityInvitation

EMAILS = ("alpha-e2e-desktop@example.test", "alpha-e2e-mobile@example.test")

if __name__ == "__main__":
    expected = (Path(__file__).resolve().parents[1] / ".e2e" / "relapaw-e2e.db").resolve()
    url = make_url(settings.database_url)
    configured = Path(url.database or "")
    if not configured.is_absolute():
        configured = (Path.cwd() / configured).resolve()
    if settings.environment != "test" or url.drivername != "sqlite" or configured != expected or not os.environ.get("RELAPAW_E2E_RUN_ID"):
        raise RuntimeError("E2E bootstrap refuses non-test databases")
    with SessionLocal() as db:
        for email in EMAILS:
            subject = identity_adapter.subject_for(email)
            assert subject is not None
            existing = db.scalar(select(IdentityInvitation).where(IdentityInvitation.provider == "local-invite", IdentityInvitation.subject == subject))
            if existing is None:
                db.add(IdentityInvitation(provider="local-invite", subject=subject, status="PENDING"))
        db.commit()
