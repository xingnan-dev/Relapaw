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


class DangerSignal(StringEnum):
    BREATHING_DIFFICULTY = "breathing_difficulty"
    PROLONGED_SEIZURE = "prolonged_seizure"
    COLLAPSE_OR_UNABLE_TO_STAND = "collapse_or_unable_to_stand"
    SEVERE_BLEEDING = "severe_bleeding"
    SUSPECTED_POISONING = "suspected_poisoning"
    OTHER_URGENT_CONCERN = "other_urgent_concern"


class EvidenceSourceType(StringEnum):
    RAW_OWNER_INPUT = "RAW_OWNER_INPUT"
    OBSERVATION = "OBSERVATION"
    OWNER_INTERPRETATION = "OWNER_INTERPRETATION"
    FOLLOW_UP = "FOLLOW_UP"


class FollowUpStatus(StringEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class FollowUpOutcome(StringEnum):
    PERSISTING = "PERSISTING"
    IMPROVED = "IMPROVED"
    WORSENED = "WORSENED"
    RESOLVED = "RESOLVED"
    NEW_SIGNS = "NEW_SIGNS"


class AnalysisRunStatus(StringEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED_BY_SAFETY = "BLOCKED_BY_SAFETY"


class ClaimStatus(StringEnum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class ClaimConfidence(StringEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EvidenceRole(StringEnum):
    SUPPORTS = "SUPPORTS"
    LIMITS = "LIMITS"
    CONTEXT = "CONTEXT"


class UncertaintyKind(StringEnum):
    MISSING_CONTEXT = "MISSING_CONTEXT"
    ALTERNATIVE_EXPLANATION = "ALTERNATIVE_EXPLANATION"
    LIMITED_OBSERVATION = "LIMITED_OBSERVATION"
    OTHER = "OTHER"


class ConfirmationDecision(StringEnum):
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class MemoryDecisionType(StringEnum):
    INCLUDE = "INCLUDE"
    WITHDRAW = "WITHDRAW"


class MemoryCandidateState(StringEnum):
    ELIGIBLE = "ELIGIBLE"
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"
    STALE = "STALE"


class LifeEventType(StringEnum):
    MOVING = "moving"
    NEW_PET = "new_pet"
    OWNER_ABSENCE = "owner_absence"
    VISITOR = "visitor"
    SURGERY = "surgery"
    DIET_CHANGE = "diet_change"
    ENVIRONMENT_CHANGE = "environment_change"
    OTHER = "other"
