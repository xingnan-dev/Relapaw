from typing import Any

from app.models import OwnerProfile


def consented_caregiver_context(profile: OwnerProfile | None) -> dict[str, Any]:
    """Return only fields the owner explicitly allowed for a new AI request."""
    if profile is None or not profile.ai_context_enabled:
        return {}
    allowed = set(profile.ai_context_fields or [])
    return {field: getattr(profile, field) for field in allowed if hasattr(profile, field) and getattr(profile, field) is not None}
