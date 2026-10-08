from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Episode


def get_pet_timeline(db: Session, pet_id: int, page: int, page_size: int) -> tuple[list[Episode], int]:
    total = db.scalar(select(func.count(Episode.id)).where(Episode.pet_id == pet_id)) or 0
    statement = (
        select(Episode)
        .where(Episode.pet_id == pet_id)
        .options(selectinload(Episode.observations), selectinload(Episode.owner_interpretations))
        .order_by(Episode.happened_at.desc(), Episode.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(statement).all()), total
