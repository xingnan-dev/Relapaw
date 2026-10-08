from enum import Enum


class StringEnum(str, Enum):
    """Stable API values stored as strings for SQLite/PostgreSQL portability."""


class SafetyStatus(StringEnum):
    NORMAL = "NORMAL"
    NEED_MORE_INFO = "NEED_MORE_INFO"
    ESCALATE_TO_VET = "ESCALATE_TO_VET"


class ObservationPlanStatus(StringEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class VeterinaryEscalationStatus(StringEnum):
    OPEN = "OPEN"
    SHARED_WITH_VET = "SHARED_WITH_VET"
    CLOSED = "CLOSED"


class ObservationSourceType(StringEnum):
    OWNER_DIRECT = "owner_direct"
    OWNER_MEDIA_REVIEW = "owner_media_review"
    MANUAL_IMPORT = "manual_import"


class LifeEventType(StringEnum):
    MOVING = "moving"
    NEW_PET = "new_pet"
    OWNER_ABSENCE = "owner_absence"
    VISITOR = "visitor"
    SURGERY = "surgery"
    DIET_CHANGE = "diet_change"
    ENVIRONMENT_CHANGE = "environment_change"
    OTHER = "other"
