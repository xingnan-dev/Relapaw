from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MediaAttachment


def media_paths_for_record(db: Session, media_dir: Path, field, record_id: int) -> list[Path]:
    """Collect storage paths before a concrete record cascade is committed."""
    keys = db.scalars(select(MediaAttachment.storage_key).where(field == record_id)).all()
    return [media_dir / key for key in keys]
