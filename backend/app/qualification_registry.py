"""Operator CLI for the database-backed runtime qualification record.

This command never reads or prints provider credentials or model outputs.
"""
import argparse

from app.db.session import SessionLocal
from app.domain.model_qualification import QUALIFICATION_ID
from app.models import ModelQualification
from app.services.model_qualification import revoke_qualification


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect or revoke a model qualification")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    revoke = subparsers.add_parser("revoke")
    revoke.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    with SessionLocal() as db:
        record = db.get(ModelQualification, QUALIFICATION_ID)
        if record is None:
            print(f"qualification_id={QUALIFICATION_ID} status=MISSING")
            return 1
        if args.command == "revoke":
            revoke_qualification(db, QUALIFICATION_ID, args.reason)
            db.commit()
        print(f"qualification_id={record.qualification_id} status={record.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
