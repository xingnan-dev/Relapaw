"""Repository-bound model qualification records.

Entries may only be added after the matching provider/model/contracts have passed
the documented evaluation and the approval evidence is available for review.
An environment variable alone can never create a qualification.
"""

from typing import Final


MODEL_QUALIFICATIONS: Final[dict[str, dict[str, str]]] = {}
