from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.config import Settings
from app.db.base import Base
from app.demo.invite_email import invite_email
from app.models import EmailOtpChallenge, IdentityInvitation
from app.services.identity import (
    DatabaseEmailOtpIdentityAdapter,
    IdentityDeliveryError,
    IdentityRateLimitError,
    IdentityVerificationError,
    ResendEmailDeliveryAdapter,
)


class FakeEmailDelivery:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.messages: list[dict[str, object]] = []

    def send_code(self, email: str, code: str, *, expires_minutes: int, idempotency_key: str) -> None:
        if self.fail:
            raise IdentityDeliveryError("synthetic delivery failure")
        self.messages.append({
            "email": email,
            "code": code,
            "expires_minutes": expires_minutes,
            "idempotency_key": idempotency_key,
        })


@pytest.fixture
def otp_runtime():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        RELAPAW_ENV="test",
        RELAPAW_EMAIL_IDENTITY_MODE="local",
        RELAPAW_SESSION_PEPPER=SecretStr("test-pepper-that-is-long-and-private"),
        RELAPAW_OTP_EXPIRY_MINUTES=10,
        RELAPAW_OTP_MAX_ATTEMPTS=5,
        RELAPAW_OTP_RESEND_COOLDOWN_SECONDS=60,
        RELAPAW_OTP_EMAIL_REQUESTS_PER_HOUR=5,
        RELAPAW_OTP_SOURCE_REQUESTS_PER_HOUR=20,
        RELAPAW_OTP_VERIFY_ATTEMPTS_PER_15_MINUTES=20,
    )
    yield sessions, settings
    Base.metadata.drop_all(engine)


def invite(db, adapter: DatabaseEmailOtpIdentityAdapter, email: str) -> None:
    subject = adapter.subject_for(email)
    assert subject is not None
    db.add(IdentityInvitation(provider="email-otp", subject=subject, status="PENDING"))
    db.commit()


def test_random_hashed_code_is_single_use_and_expires_in_ten_minutes(otp_runtime):
    sessions, settings = otp_runtime
    delivery = FakeEmailDelivery()
    adapter = DatabaseEmailOtpIdentityAdapter(settings, delivery)
    with sessions() as db:
        invite(db, adapter, "Owner@Example.Test")
        adapter.request_challenge(" owner@example.test ", db=db, source="127.0.0.1")
        assert len(delivery.messages) == 1
        message = delivery.messages[0]
        code = str(message["code"])
        assert len(code) == 6 and code.isdigit()
        challenge = db.scalar(select(EmailOtpChallenge))
        assert challenge is not None
        assert challenge.code_hash != code
        assert challenge.expires_at.replace(tzinfo=UTC) - challenge.created_at.replace(tzinfo=UTC) == timedelta(minutes=10)
        identity = adapter.verify_challenge("owner@example.test", code, db=db, source="127.0.0.1")
        assert identity.provider == "email-otp"
        with pytest.raises(IdentityVerificationError):
            adapter.verify_challenge("owner@example.test", code, db=db, source="127.0.0.1")


def test_wrong_code_attempt_limit_invalidates_challenge(otp_runtime):
    sessions, settings = otp_runtime
    delivery = FakeEmailDelivery()
    adapter = DatabaseEmailOtpIdentityAdapter(settings, delivery)
    with sessions() as db:
        invite(db, adapter, "owner@example.test")
        adapter.request_challenge("owner@example.test", db=db, source="source-a")
        correct_code = str(delivery.messages[0]["code"])
        for _ in range(settings.otp_max_attempts):
            with pytest.raises(IdentityVerificationError):
                adapter.verify_challenge("owner@example.test", "999999", db=db, source="source-a")
        challenge = db.scalar(select(EmailOtpChallenge))
        assert challenge is not None and challenge.attempt_count == settings.otp_max_attempts
        assert challenge.invalidated_at is not None
        with pytest.raises(IdentityVerificationError):
            adapter.verify_challenge("owner@example.test", correct_code, db=db, source="source-a")


def test_expired_code_is_rejected(otp_runtime):
    sessions, settings = otp_runtime
    delivery = FakeEmailDelivery()
    adapter = DatabaseEmailOtpIdentityAdapter(settings, delivery)
    with sessions() as db:
        invite(db, adapter, "owner@example.test")
        adapter.request_challenge("owner@example.test", db=db, source="source-a")
        challenge = db.scalar(select(EmailOtpChallenge))
        assert challenge is not None
        challenge.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
        with pytest.raises(IdentityVerificationError):
            adapter.verify_challenge(
                "owner@example.test", str(delivery.messages[0]["code"]), db=db, source="source-a"
            )


def test_delivery_failure_leaves_no_verifiable_challenge(otp_runtime):
    sessions, settings = otp_runtime
    delivery = FakeEmailDelivery(fail=True)
    adapter = DatabaseEmailOtpIdentityAdapter(settings, delivery)
    with sessions() as db:
        invite(db, adapter, "owner@example.test")
        with pytest.raises(IdentityDeliveryError):
            adapter.request_challenge("owner@example.test", db=db, source="source-a")
        assert db.scalar(select(func.count()).select_from(EmailOtpChallenge)) == 0


def test_unknown_email_is_indistinguishable_and_not_delivered(otp_runtime):
    sessions, settings = otp_runtime
    delivery = FakeEmailDelivery()
    adapter = DatabaseEmailOtpIdentityAdapter(settings, delivery)
    with sessions() as db:
        adapter.request_challenge("unknown@example.test", db=db, source="source-a")
        assert delivery.messages == []
        assert db.scalar(select(func.count()).select_from(EmailOtpChallenge)) == 0


def test_resend_cooldown_and_email_source_rate_limits(otp_runtime, monkeypatch):
    sessions, settings = otp_runtime
    delivery = FakeEmailDelivery()
    adapter = DatabaseEmailOtpIdentityAdapter(settings, delivery)
    with sessions() as db:
        invite(db, adapter, "owner@example.test")
        adapter.request_challenge("owner@example.test", db=db, source="source-a")
        with pytest.raises(IdentityRateLimitError):
            adapter.request_challenge("owner@example.test", db=db, source="source-a")

    monkeypatch.setattr(settings, "otp_email_requests_per_hour", 1)
    with sessions() as db:
        with pytest.raises(IdentityRateLimitError):
            adapter.request_challenge("owner@example.test", db=db, source="source-b")

    monkeypatch.setattr(settings, "otp_source_requests_per_hour", 1)
    with sessions() as db:
        with pytest.raises(IdentityRateLimitError):
            adapter.request_challenge("another@example.test", db=db, source="source-a")


def test_staging_and_production_reject_local_fixed_code_mode():
    base = {
        "_env_file": None,
        "RELAPAW_ENV": "production",
        "RELAPAW_DEPLOYMENT_VERSION": "release-test",
        "database_url": "postgresql+psycopg://user:pass@db/name",
        "cors_origins": ["https://beta.relapaw.example"],
        "RELAPAW_SESSION_PEPPER": "a-production-secret-that-is-at-least-32-characters",
        "RELAPAW_TERMS_VERSION": "terms-v1",
        "RELAPAW_PRIVACY_VERSION": "privacy-v1",
        "RELAPAW_LEGAL_DOCUMENTS_APPROVED": True,
        "RELAPAW_MEDICAL_REVIEW_STATUS": "APPROVED",
    }
    with pytest.raises(ValueError, match="Resend email identity mode"):
        Settings(**base)
    with pytest.raises(ValueError, match="forbidden"):
        Settings(
            **base,
            RELAPAW_EMAIL_IDENTITY_MODE="resend",
            RESEND_API_KEY="test-placeholder-not-a-real-secret",
            RELAPAW_RESEND_FROM_EMAIL="login@relapaw.example",
            RELAPAW_LOCAL_INVITE_CODE="fixed-code-is-forbidden",
        )
    with pytest.raises(ValueError, match="local verification"):
        Settings(
            **base,
            RELAPAW_EMAIL_IDENTITY_MODE="resend",
            RESEND_API_KEY="test-placeholder-not-a-real-secret",
            RELAPAW_RESEND_FROM_EMAIL="login@relapaw.example",
            RELAPAW_TEST_RECIPIENT_EMAIL="owner@example.test",
        )


def test_resend_adapter_uses_fake_http_boundary_without_network(monkeypatch):
    captured: dict[str, object] = {}

    class Response:
        def raise_for_status(self):
            return None

    def fake_post(url, **kwargs):
        captured.update({"url": url, **kwargs})
        return Response()

    monkeypatch.setattr("app.services.identity.httpx.post", fake_post)
    settings = Settings(
        _env_file=None,
        RELAPAW_ENV="test",
        RELAPAW_EMAIL_IDENTITY_MODE="resend",
        RESEND_API_KEY="test-placeholder-not-a-real-secret",
        RELAPAW_RESEND_FROM_EMAIL="login@relapaw.example",
    )
    ResendEmailDeliveryAdapter(settings).send_code(
        "owner@example.test", "123456", expires_minutes=10, idempotency_key="test-idempotency"
    )
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["json"] == {
        "from": "login@relapaw.example",
        "to": ["owner@example.test"],
        "subject": "你的 Relapaw 登录验证码",
        "text": "你的 Relapaw 验证码是 123456。验证码将在 10 分钟后失效；请勿转发给他人。",
    }
    assert captured["headers"]["Idempotency-Key"] == "test-idempotency"


def test_resend_invitation_stores_only_hashed_subject(otp_runtime, monkeypatch):
    sessions, settings = otp_runtime
    monkeypatch.setattr(settings, "email_identity_mode", "resend")
    adapter = DatabaseEmailOtpIdentityAdapter(settings, FakeEmailDelivery())
    invitation = invite_email(
        "owner@example.test", session_factory=sessions, adapter=adapter
    )
    assert invitation.provider == "email-otp"
    assert invitation.subject == adapter.subject_for("owner@example.test")
    assert "owner@example.test" not in invitation.subject
