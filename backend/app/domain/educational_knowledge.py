"""Local, versioned educational examples. Never diagnostic or treatment advice."""

from typing import Final

KNOWLEDGE_SET: Final[dict] = {
    "version": "local-education/2026-10-21-v1",
    "review_status": "UNREVIEWED_EXAMPLE",
    "review_note": "Local example content; not formally approved by a veterinarian.",
    "entries": [
        {
            "id": "observe-context-change",
            "species": ["cat", "dog", "other"],
            "title": "Record context together with the behavior",
            "summary": "Repeated observations are easier to compare when time, place, duration and what happened immediately beforehand are recorded.",
            "topics": ["context", "duration", "trigger"],
            "source": {"title": "Relapaw local observation guide", "version": "2026-10-21", "locator": "section/context", "url": None},
        },
        {
            "id": "observe-routine",
            "species": ["cat", "dog", "other"],
            "title": "Compare records with the same animal's routine",
            "summary": "A dated series of factual records can show whether frequency or duration differs from that animal's recorded routine; it does not identify a cause.",
            "topics": ["frequency", "duration", "baseline"],
            "source": {"title": "Relapaw local observation guide", "version": "2026-10-21", "locator": "section/routine", "url": None},
        },
        {
            "id": "observe-interactions",
            "species": ["cat", "dog", "other"],
            "title": "Describe interactions without assigning intent",
            "summary": "Record distance, approach, retreat, contact, resource location and timing separately from any interpretation of intent or emotion.",
            "topics": ["interaction", "relationship", "location"],
            "source": {"title": "Relapaw local observation guide", "version": "2026-10-21", "locator": "section/interactions", "url": None},
        },
    ],
}
