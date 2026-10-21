"""Apply documented privacy retention rules.

Run this command from the application environment on a daily schedule. It is
idempotent: accounts are selected only while pending and due, and audit rows are
selected only after their retention window has elapsed.
"""

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.privacy import purge_due_accounts, purge_expired_audit_events


def main() -> int:
    with SessionLocal() as db:
        accounts = purge_due_accounts(db, settings)
        audit_events = purge_expired_audit_events(db, settings)
    print(f"privacy retention complete: accounts={accounts}, audit_events={audit_events}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
