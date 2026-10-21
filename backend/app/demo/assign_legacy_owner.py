"""Explicitly quarantine legacy local/demo rows under a disabled user.

Run only after migration 0009 and before 0010. This command never assigns rows to an
active or real user and requires an unambiguous opt-in flag.
"""
import argparse
from uuid import UUID, uuid5
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal


LEGACY_DEMO_USER_ID = "00000000-0000-0000-0000-00000000d3e0"
LEGACY_PROFILE_NAMESPACE = UUID("00000000-0000-0000-0000-00000000d3e1")


def _ensure_disabled_user(db: Session, user_id: str) -> None:
    status = db.scalar(text("SELECT status FROM users WHERE id = :user_id"), {"user_id": user_id})
    if status is None:
        db.execute(
            text("INSERT INTO users (id, status) VALUES (:user_id, 'DISABLED')"),
            {"user_id": user_id},
        )
    elif status != "DISABLED":
        raise RuntimeError("A reserved legacy quarantine user must remain DISABLED")


def assign_legacy_demo_owner(db: Session, *, allowed: bool) -> tuple[int, int]:
    if not allowed:
        raise RuntimeError("Explicit --allow-legacy-demo-data confirmation is required")
    tables = set(inspect(db.get_bind()).get_table_names())
    if not {"users", "pets", "owner_profiles", "alembic_version"}.issubset(tables):
        raise RuntimeError("Identity migration A (20261020_0009) must be applied first")
    revision = db.scalar(text("SELECT version_num FROM alembic_version"))
    if revision != "20261020_0009":
        raise RuntimeError("Legacy assignment is only allowed at revision 20261020_0009")

    _ensure_disabled_user(db, LEGACY_DEMO_USER_ID)

    pet_count = db.execute(
        text("UPDATE pets SET owner_user_id = :user_id WHERE owner_user_id IS NULL"),
        {"user_id": LEGACY_DEMO_USER_ID},
    ).rowcount
    profile_ids = list(db.scalars(text(
        "SELECT id FROM owner_profiles WHERE user_id IS NULL ORDER BY id"
    )).all())
    for index, profile_id in enumerate(profile_ids):
        # owner_profiles.user_id is unique. Preserve every legal legacy row by
        # assigning a deterministic disabled quarantine identity per profile.
        user_id = LEGACY_DEMO_USER_ID if index == 0 else str(
            uuid5(LEGACY_PROFILE_NAMESPACE, f"owner-profile:{profile_id}")
        )
        _ensure_disabled_user(db, user_id)
        db.execute(
            text("UPDATE owner_profiles SET user_id = :user_id WHERE id = :profile_id AND user_id IS NULL"),
            {"user_id": user_id, "profile_id": profile_id},
        )
    db.commit()
    return pet_count, len(profile_ids)


def main() -> int:
    parser = argparse.ArgumentParser(description="Quarantine legacy demo rows under a disabled user")
    parser.add_argument("--allow-legacy-demo-data", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        pets, profiles = assign_legacy_demo_owner(db, allowed=args.allow_legacy_demo_data)
    print(f"assigned legacy demo rows: pets={pets}, owner_profiles={profiles}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
