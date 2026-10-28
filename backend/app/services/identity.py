from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest, new as hmac_new
from secrets import randbelow
from typing import Protocol
from threading import Lock
from time import monotonic

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import EmailOtpChallenge, EmailOtpRateLimitEvent, IdentityInvitation


class IdentityVerificationError(Exception):
    pass


class IdentityRateLimitError(Exception):
    pass


class IdentityDeliveryError(Exception):
    pass


@dataclass(frozen=True)
class VerifiedIdentity:
    provider: str
    subject: str


class IdentityAdapter(Protocol):
    def request_challenge(self, email: str, *, db: Session | None = None, source: str = "") -> None: ...
    def verify_challenge(self, email: str, code: str, *, db: Session | None = None, source: str = "") -> VerifiedIdentity: ...


class EmailDeliveryAdapter(Protocol):
    def send_code(self, email: str, code: str, *, expires_minutes: int, idempotency_key: str) -> None: ...


class ResendEmailDeliveryAdapter:
    """Minimal Resend boundary. Secrets and message content are never logged."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def send_code(self, email: str, code: str, *, expires_minutes: int, idempotency_key: str) -> None:
        api_key = self._settings.resend_api_key
        sender = self._settings.resend_from_email
        if api_key is None or not sender:
            raise IdentityDeliveryError("Email delivery is not configured")
        try:
            response = httpx.post(
                self._settings.resend_api_url,
                headers={
                    "Authorization": f"Bearer {api_key.get_secret_value()}",
                    "Idempotency-Key": idempotency_key,
                    "Content-Type": "application/json",
                },
                json={
                    "from": sender,
                    "to": [email],
                    "subject": "你的 Relapaw 登录验证码",
                    "text": f"你的 Relapaw 验证码是 {code}。验证码将在 {expires_minutes} 分钟后失效；请勿转发给他人。",
                },
                timeout=10.0,
            )
            response.raise_for_status()
        except (httpx.HTTPError, ValueError) as exc:
            raise IdentityDeliveryError("Email delivery failed") from exc


def _normalized_email(email: str) -> str | None:
    value = email.strip().casefold()
    local, separator, domain = value.rpartition("@")
    if not separator or not local or "." not in domain or any(character.isspace() for character in value):
        return None
    return value


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class DatabaseEmailOtpIdentityAdapter:
    provider = "email-otp"

    def __init__(self, settings: Settings, delivery: EmailDeliveryAdapter):
        self._settings = settings
        self._delivery = delivery

    def _digest(self, namespace: str, value: str) -> str:
        return hmac_new(
            self._settings.session_pepper.get_secret_value().encode(),
            f"{namespace}:{value}".encode(),
            sha256,
        ).hexdigest()

    def subject_for(self, email: str) -> str | None:
        normalized = _normalized_email(email)
        return None if normalized is None else self._digest("email-subject", normalized)

    def _source_hash(self, source: str) -> str:
        return self._digest("request-source", source.strip() or "unknown")

    def _code_hash(self, challenge_id: str, code: str) -> str:
        return self._digest("otp-code", f"{challenge_id}:{code}")

    def _check_limit(self, db: Session, *, action: str, subject: str, source_hash: str, now: datetime) -> None:
        if action == "REQUEST":
            window = now - timedelta(hours=1)
            email_limit = self._settings.otp_email_requests_per_hour
            source_limit = self._settings.otp_source_requests_per_hour
        else:
            window = now - timedelta(minutes=15)
            email_limit = source_limit = self._settings.otp_verify_attempts_per_15_minutes
        email_count = db.scalar(select(func.count()).select_from(EmailOtpRateLimitEvent).where(
            EmailOtpRateLimitEvent.action == action,
            EmailOtpRateLimitEvent.subject_hash == subject,
            EmailOtpRateLimitEvent.created_at >= window,
        )) or 0
        source_count = db.scalar(select(func.count()).select_from(EmailOtpRateLimitEvent).where(
            EmailOtpRateLimitEvent.action == action,
            EmailOtpRateLimitEvent.source_hash == source_hash,
            EmailOtpRateLimitEvent.created_at >= window,
        )) or 0
        if email_count >= email_limit or source_count >= source_limit:
            raise IdentityRateLimitError("Challenge rate limit exceeded")
        if action == "REQUEST":
            latest = db.scalar(select(EmailOtpRateLimitEvent.created_at).where(
                EmailOtpRateLimitEvent.action == "REQUEST",
                EmailOtpRateLimitEvent.subject_hash == subject,
            ).order_by(EmailOtpRateLimitEvent.created_at.desc()).limit(1))
            if latest is not None and _utc(latest) + timedelta(seconds=self._settings.otp_resend_cooldown_seconds) > now:
                raise IdentityRateLimitError("Challenge resend cooldown is active")

    def _record_attempt(self, db: Session, *, action: str, subject: str, source_hash: str, now: datetime) -> None:
        db.add(EmailOtpRateLimitEvent(
            action=action, subject_hash=subject, source_hash=source_hash, created_at=now
        ))
        db.commit()

    def request_challenge(self, email: str, *, db: Session | None = None, source: str = "") -> None:
        if db is None:
            raise RuntimeError("Database session is required for email OTP")
        normalized = _normalized_email(email)
        subject = self.subject_for(email)
        if normalized is None or subject is None:
            return
        now = datetime.now(UTC)
        source_hash = self._source_hash(source)
        self._check_limit(db, action="REQUEST", subject=subject, source_hash=source_hash, now=now)
        self._record_attempt(db, action="REQUEST", subject=subject, source_hash=source_hash, now=now)

        invitation = db.scalar(select(IdentityInvitation.id).where(
            IdentityInvitation.provider == self.provider,
            IdentityInvitation.subject == subject,
            IdentityInvitation.status.in_(["PENDING", "ACCEPTED"]),
        ))
        if invitation is None:
            return

        challenge = EmailOtpChallenge(
            subject=subject,
            code_hash="pending",
            source_hash=source_hash,
            expires_at=now + timedelta(minutes=self._settings.otp_expiry_minutes),
            created_at=now,
        )
        db.add(challenge)
        db.flush()
        code = f"{randbelow(1_000_000):06d}"
        challenge.code_hash = self._code_hash(challenge.id, code)
        db.execute(update(EmailOtpChallenge).where(
            EmailOtpChallenge.subject == subject,
            EmailOtpChallenge.id != challenge.id,
            EmailOtpChallenge.consumed_at.is_(None),
            EmailOtpChallenge.invalidated_at.is_(None),
        ).values(invalidated_at=now))
        try:
            self._delivery.send_code(
                normalized,
                code,
                expires_minutes=self._settings.otp_expiry_minutes,
                idempotency_key=f"relapaw-otp-{challenge.id}",
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

    def verify_challenge(self, email: str, code: str, *, db: Session | None = None, source: str = "") -> VerifiedIdentity:
        if db is None:
            raise RuntimeError("Database session is required for email OTP")
        subject = self.subject_for(email)
        if subject is None:
            raise IdentityVerificationError("Challenge verification failed")
        now = datetime.now(UTC)
        source_hash = self._source_hash(source)
        self._check_limit(db, action="VERIFY", subject=subject, source_hash=source_hash, now=now)
        self._record_attempt(db, action="VERIFY", subject=subject, source_hash=source_hash, now=now)
        challenge = db.scalar(select(EmailOtpChallenge).where(
            EmailOtpChallenge.subject == subject,
            EmailOtpChallenge.consumed_at.is_(None),
            EmailOtpChallenge.invalidated_at.is_(None),
        ).order_by(EmailOtpChallenge.created_at.desc()).with_for_update())
        if challenge is None or _utc(challenge.expires_at) <= now or challenge.attempt_count >= self._settings.otp_max_attempts:
            raise IdentityVerificationError("Challenge verification failed")
        if not compare_digest(challenge.code_hash, self._code_hash(challenge.id, code)):
            challenge.attempt_count += 1
            if challenge.attempt_count >= self._settings.otp_max_attempts:
                challenge.invalidated_at = now
            db.commit()
            raise IdentityVerificationError("Challenge verification failed")
        challenge.consumed_at = now
        db.commit()
        return VerifiedIdentity(provider=self.provider, subject=subject)


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
        normalized = _normalized_email(email)
        if normalized is None:
            return None
        return hmac_new(
            self._settings.session_pepper.get_secret_value().encode(),
            normalized.encode(),
            sha256,
        ).hexdigest()

    def request_challenge(self, email: str, *, db: Session | None = None, source: str = "") -> None:
        # Delivery belongs to a production adapter. Local challenges are deliberately
        # indistinguishable and short-lived, and the configured code is one-use.
        subject = self.subject_for(email)
        if subject is not None:
            with self._lock:
                self._challenges[subject] = (monotonic() + 600, 0)

    def verify_challenge(self, email: str, code: str, *, db: Session | None = None, source: str = "") -> VerifiedIdentity:
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


def build_identity_adapter(settings: Settings) -> IdentityAdapter:
    if settings.email_identity_mode == "resend":
        return DatabaseEmailOtpIdentityAdapter(settings, ResendEmailDeliveryAdapter(settings))
    return LocalInviteIdentityAdapter(settings)
