"""Repository-controlled, non-diagnostic educational knowledge.

Only entries with ``APPROVED`` status and no withdrawal timestamp may enter a
runtime prompt. Medical triage remains in ``medical_safety.py`` and cannot be
approved through this manifest.
"""

from datetime import datetime, timezone
from typing import Final


KNOWLEDGE_SET: Final[dict] = {
    "version": "controlled-education/2026-10-25-v1",
    "review_status": "APPROVED",
    "review_note": (
        "Internally reviewed, non-medical recording guidance. It is not a "
        "veterinary approval and must not be used for diagnosis or treatment."
    ),
    "entries": [
        {
            "id": "observe-context-change", "version": "2026-10-25-v1",
            "species": ["cat", "dog", "other"],
            "title": "Record context together with the behavior",
            "summary": "Repeated observations are easier to compare when time, place, duration and what happened immediately beforehand are recorded.",
            "topics": ["context", "duration", "trigger"],
            "published_at": "2026-10-25", "review_status": "APPROVED",
            "reviewed_at": "2026-10-25", "withdrawn_at": None,
            "scope": "recording_method_only",
            "source": {"title": "Relapaw controlled observation guide", "version": "2026-10-25", "locator": "section/context", "url": None},
        },
        {
            "id": "observe-routine", "version": "2026-10-25-v1",
            "species": ["cat", "dog", "other"],
            "title": "Compare records with the same animal's routine",
            "summary": "A dated series of factual records can show whether frequency or duration differs from that animal's recorded routine; it does not identify a cause.",
            "topics": ["frequency", "duration", "baseline"],
            "published_at": "2026-10-25", "review_status": "APPROVED",
            "reviewed_at": "2026-10-25", "withdrawn_at": None,
            "scope": "recording_method_only",
            "source": {"title": "Relapaw controlled observation guide", "version": "2026-10-25", "locator": "section/routine", "url": None},
        },
        {
            "id": "observe-interactions", "version": "2026-10-25-v1",
            "species": ["cat", "dog", "other"],
            "title": "Describe interactions without assigning intent",
            "summary": "Record distance, approach, retreat, contact, resource location and timing separately from any interpretation of intent or emotion.",
            "topics": ["interaction", "relationship", "location"],
            "published_at": "2026-10-25", "review_status": "APPROVED",
            "reviewed_at": "2026-10-25", "withdrawn_at": None,
            "scope": "recording_method_only",
            "source": {"title": "Relapaw controlled observation guide", "version": "2026-10-25", "locator": "section/interactions", "url": None},
        },
    ],
}


def approved_knowledge_entries(*, species: str, topics: set[str] | None = None) -> list[dict]:
    """Return a detached snapshot of the approved runtime subset."""
    normalized_species = species.strip().lower()
    known_species = {value for entry in KNOWLEDGE_SET["entries"] for value in entry["species"] if value != "other"}
    match_species = normalized_species if normalized_species in known_species else "other"
    selected: list[dict] = []
    for entry in KNOWLEDGE_SET["entries"]:
        if entry["review_status"] != "APPROVED" or entry["withdrawn_at"] is not None:
            continue
        if match_species not in entry["species"]:
            continue
        if topics and not topics.intersection(entry["topics"]):
            continue
        selected.append({**entry, "source": dict(entry["source"])})
    return selected


def knowledge_snapshot(*, species: str, topics: set[str] | None = None) -> dict:
    return {
        "set_version": KNOWLEDGE_SET["version"],
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "entries": approved_knowledge_entries(species=species, topics=topics),
    }
