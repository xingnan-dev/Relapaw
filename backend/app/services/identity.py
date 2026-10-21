from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest, new as hmac_new
from typing import Protocol
from threading import Lock
from time import monotonic

from app.core.config import Settings


class IdentityVerificationError(Exception):
    pass


@dataclass(frozen=True)
class VerifiedIdentity:
    provider: str
    subject: str


class IdentityAdapter(Protocol):
    def request_challenge(self, email: str) -> None: ...
    def verify_challenge(self, email: str, code: str) -> VerifiedIdentity: ...


class LocalInviteIdentityAdapter:
    """Local-only adapter used to exercise the complete auth boundary without a vendor.

    It deliberately stores no email: the stable subject is a peppered digest. This
    adapter is rejected by Settings in staging and production.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._challenges: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    def subject_for(self, email: str) -> str | None:
        normalized = email.strip().casefold()
        if not normalized or "@" not in normalized:
            return None
        return hmac_new(
            self._settings.session_pepper.get_secret_value().encode(),
            normalized.encode(),
            sha256,
        ).hexdigest()

    def request_challenge(self, email: str) -> None:
        # Delivery belongs to a production adapter. Local challenges are deliberately
        # indistinguishable and short-lived, and the configured code is one-use.
        subject = self.subject_for(email)
        if subject is not None:
            with self._lock:
                self._challenges[subject] = (monotonic() + 600, 0)

    def verify_challenge(self, email: str, code: str) -> VerifiedIdentity:
        configured = self._settings.local_invite_code
        subject = self.subject_for(email)
        if configured is None or subject is None:
            raise IdentityVerificationError("Challenge verification failed")
        with self._lock:
            challenge = self._challenges.get(subject)
            if challenge is None or challenge[0] < monotonic() or challenge[1] >= 5:
                self._challenges.pop(subject, None)
                raise IdentityVerificationError("Challenge verification failed")
            if not compare_digest(code, configured.get_secret_value()):
                self._challenges[subject] = (challenge[0], challenge[1] + 1)
                raise IdentityVerificationError("Challenge verification failed")
            self._challenges.pop(subject, None)
        return VerifiedIdentity(provider="local-invite", subject=subject)
