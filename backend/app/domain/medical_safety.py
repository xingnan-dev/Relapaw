"""Versioned, reviewable medical-safety content.

This is routing content, not diagnostic knowledge. Production configuration refuses
to start until the selected version has an externally recorded veterinarian approval.
"""

from typing import Final


MEDICAL_SAFETY_MANIFEST: Final[dict] = {
    "version": "medical-safety/v1",
    "status": "PENDING",
    "scope": "owner-selected urgent routing signals; no diagnosis or treatment advice",
    "required_action": "contact_a_veterinarian_promptly",
    "signals": {
        "breathing_difficulty": "Difficulty breathing",
        "prolonged_seizure": "Prolonged seizure",
        "collapse_or_unable_to_stand": "Collapse or unable to stand",
        "severe_bleeding": "Severe bleeding",
        "suspected_poisoning": "Suspected poisoning",
        "other_urgent_concern": "Other urgent concern",
    },
    "review": {
        "reviewer_name": None,
        "reviewer_credential": None,
        "reviewed_at": None,
        "approval_reference": None,
    },
}
