from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
from pydantic import SecretStr
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.api.deps import require_auth_context, require_csrf, require_current_user
from app.db.session import get_db
from app.main import app
from app.api.router import api_router
from app.api.routes.auth import _require_valid_locked_invitation, identity_adapter
from app.api.errors import APIError
from app.models import AnalysisRun, Claim, Episode, IdentityInvitation, MemoryCandidate, User, UserSession


ORIGIN = "http://localhost:5173"
INVITE_CODE = "local-test-invite"


@pytest.fixture
def auth_runtime(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        with sessions() as db:
            yield db

    monkeypatch.setattr(settings, "local_invite_code", SecretStr(INVITE_CODE))
    with sessions() as db:
        for email in ("alice@example.test", "bob@example.test"):
            subject = identity_adapter.subject_for(email)
            assert subject is not None
            db.add(IdentityInvitation(provider="local-invite", subject=subject, status="PENDING"))
        db.commit()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    clients: list[TestClient] = []

    def new_client() -> TestClient:
        client = TestClient(app)
        clients.append(client)
        return client

    yield new_client, sessions
    for client in clients:
        client.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def login(client: TestClient, email: str) -> str:
    requested = client.post(
        "/api/v1/auth/otp/request", headers={"Origin": ORIGIN}, json={"email": email}
    )
    assert requested.status_code == 202
    response = client.post(
        "/api/v1/auth/otp/verify",
        headers={"Origin": ORIGIN},
        json={"email": email, "code": INVITE_CODE},
    )
    assert response.status_code == 200, response.text
    csrf = client.post("/api/v1/auth/csrf", headers={"Origin": ORIGIN})
    assert csrf.status_code == 200
    token = csrf.json()["csrf_token"]
    consent = client.post(
        "/api/v1/privacy/consent", headers=write_headers(token),
        json={
            "terms_version": settings.terms_version,
            "privacy_version": settings.privacy_version,
            "source": "ONBOARDING",
            "affirm_adult_owner": True,
        },
    )
    assert consent.status_code in {200, 201}, consent.text
    return token


def write_headers(csrf: str, *, origin: str = ORIGIN) -> dict[str, str]:
    return {"Origin": origin, "X-CSRF-Token": csrf}


def test_current_policy_consent_is_required_and_version_bound(auth_runtime):
    new_client, _sessions = auth_runtime
    client = new_client()
    response = client.post(
        "/api/v1/auth/otp/request", headers={"Origin": ORIGIN}, json={"email": "alice@example.test"}
    )
    assert response.status_code == 202
    session = client.post(
        "/api/v1/auth/otp/verify",
        headers={"Origin": ORIGIN},
        json={"email": "alice@example.test", "code": INVITE_CODE},
    )
    assert session.status_code == 200
    assert session.json()["consent_required"] is True
    csrf = client.post("/api/v1/auth/csrf", headers={"Origin": ORIGIN}).json()["csrf_token"]
    blocked = client.get("/api/v1/pets")
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "CONSENT_REQUIRED"

    wrong_version = client.post(
        "/api/v1/privacy/consent", headers=write_headers(csrf),
        json={"terms_version": "old", "privacy_version": settings.privacy_version, "source": "ONBOARDING", "affirm_adult_owner": True},
    )
    assert wrong_version.status_code == 409
    no_adult_confirmation = client.post(
        "/api/v1/privacy/consent", headers=write_headers(csrf),
        json={"terms_version": settings.terms_version, "privacy_version": settings.privacy_version, "source": "ONBOARDING", "affirm_adult_owner": False},
    )
    assert no_adult_confirmation.status_code == 422

    accepted = client.post(
        "/api/v1/privacy/consent", headers=write_headers(csrf),
        json={"terms_version": settings.terms_version, "privacy_version": settings.privacy_version, "source": "ONBOARDING", "affirm_adult_owner": True},
    )
    assert accepted.status_code == 201
    assert client.get("/api/v1/pets").status_code == 200


def test_locked_invitation_is_revalidated_after_waiting_for_concurrent_changes():
    revoked = IdentityInvitation(
        provider="local-invite",
        subject="revoked-subject",
        status="REVOKED",
        accepted_user_id="user-that-was-previously-accepted",
    )
    with pytest.raises(APIError) as caught:
        _require_valid_locked_invitation(revoked, datetime.now(UTC))
    assert caught.value.status_code == 401
    assert caught.value.code == "CHALLENGE_INVALID"


def dependency_calls(route: APIRoute) -> set[object]:
    calls: set[object] = set()
    pending = list(route.dependant.dependencies)
    while pending:
        dependency = pending.pop()
        calls.add(dependency.call)
        pending.extend(dependency.dependencies)
    return calls


def test_every_business_route_has_auth_and_every_write_has_csrf():
    business_routes: list[APIRoute] = []
    for included in api_router.routes:
        router = getattr(included, "original_router", None)
        if router is None:
            continue
        business_routes.extend(
            route for route in router.routes
            if isinstance(route, APIRoute) and "auth" not in route.tags
        )
    assert business_routes
    for route in business_routes:
        calls = dependency_calls(route)
        assert require_current_user in calls or require_csrf in calls or require_auth_context in calls, route.path
        if route.methods & {"POST", "PUT", "PATCH", "DELETE"}:
            assert require_csrf in calls, route.path


def test_anonymous_business_routes_are_private_and_auth_challenges_check_origin(auth_runtime):
    new_client, _sessions = auth_runtime
    client = new_client()

    for path in ("/api/v1/pets", "/api/v1/capabilities", "/api/v1/owner-profile"):
        assert client.get(path).status_code == 401
    assert client.get("/health").status_code == 200
    assert client.post(
        "/api/v1/auth/otp/request", json={"email": "person@example.test"}
    ).status_code == 403
    assert client.post(
        "/api/v1/auth/otp/request",
        headers={"Origin": ORIGIN},
        json={"email": "person@example.test"},
    ).status_code == 202
    assert client.post(
        "/api/v1/auth/otp/verify",
        headers={"Origin": ORIGIN},
        json={"email": "person@example.test", "code": INVITE_CODE},
    ).status_code == 401


def test_login_restore_rotation_logout_expiry_and_revocation(auth_runtime):
    new_client, sessions = auth_runtime
    first = new_client()
    first_csrf = login(first, "alice@example.test")
    restored = first.get("/api/v1/auth/session")
    assert restored.status_code == 200
    user_id = restored.json()["user_id"]
    old_cookie = first.cookies.get(settings.session_cookie_name)
    assert first.post(
        "/api/v1/auth/otp/verify", headers={"Origin": ORIGIN},
        json={"email": "alice@example.test", "code": INVITE_CODE},
    ).status_code == 401

    second = new_client()
    second_csrf = login(second, "alice@example.test")
    assert second.get("/api/v1/auth/session").json()["user_id"] == user_id
    assert old_cookie != second.cookies.get(settings.session_cookie_name)
    assert first.get("/api/v1/auth/session").status_code == 401

    assert second.post(
        "/api/v1/auth/logout", headers=write_headers(second_csrf)
    ).status_code == 204
    assert second.get("/api/v1/auth/session").status_code == 401

    third = new_client()
    login(third, "alice@example.test")
    token = third.cookies.get(settings.session_cookie_name)
    assert token
    with sessions() as db:
        row = db.scalar(select(UserSession).where(
            UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
        ))
        assert row is not None
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert third.get("/api/v1/auth/session").status_code == 401

    fourth = new_client()
    login(fourth, "alice@example.test")
    with sessions() as db:
        row = db.scalar(select(UserSession).where(
            UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
        ))
        assert row is not None
        row.revoked_at = datetime.now(UTC)
        db.commit()
    assert fourth.get("/api/v1/auth/session").status_code == 401

    fifth = new_client()
    login(fifth, "alice@example.test")
    with sessions() as db:
        row = db.scalar(select(UserSession).where(
            UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
        ))
        assert row is not None
        row.last_seen_at = datetime.now(UTC) - timedelta(days=settings.session_idle_days, seconds=1)
        db.commit()
    assert fifth.get("/api/v1/auth/session").status_code == 401

    sixth = new_client()
    login(sixth, "alice@example.test")
    with sessions() as db:
        user = db.get(User, user_id); assert user is not None
        user.status = "DISABLED"
        db.commit()
    assert sixth.get("/api/v1/auth/session").status_code == 401
    assert sixth.post(
        "/api/v1/auth/otp/request", headers={"Origin": ORIGIN},
        json={"email": "alice@example.test"},
    ).status_code == 202
    assert sixth.post(
        "/api/v1/auth/otp/verify", headers={"Origin": ORIGIN},
        json={"email": "alice@example.test", "code": INVITE_CODE},
    ).status_code == 401


def test_accepted_invitation_remains_valid_after_its_invitation_window(auth_runtime):
    new_client, sessions = auth_runtime
    first = new_client()
    first_csrf = login(first, "alice@example.test")
    assert first.post("/api/v1/auth/logout", headers=write_headers(first_csrf)).status_code == 204

    subject = identity_adapter.subject_for("alice@example.test")
    assert subject is not None
    with sessions() as db:
        invitation = db.scalar(select(IdentityInvitation).where(
            IdentityInvitation.provider == "local-invite",
            IdentityInvitation.subject == subject,
        ))
        assert invitation is not None
        assert invitation.status == "ACCEPTED"
        invitation.expires_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()

    returning = new_client()
    requested = returning.post(
        "/api/v1/auth/otp/request",
        headers={"Origin": ORIGIN},
        json={"email": "alice@example.test"},
    )
    assert requested.status_code == 202
    verified = returning.post(
        "/api/v1/auth/otp/verify",
        headers={"Origin": ORIGIN},
        json={"email": "alice@example.test", "code": INVITE_CODE},
    )
    assert verified.status_code == 200


def test_cookie_writes_require_bound_csrf_and_allowed_origin(auth_runtime):
    new_client, _sessions = auth_runtime
    client = new_client()
    csrf = login(client, "alice@example.test")
    payload = {"name": "Mochi", "species": "cat"}

    assert client.post("/api/v1/pets", json=payload).status_code == 403
    assert client.post(
        "/api/v1/pets", headers=write_headers("wrong"), json=payload
    ).status_code == 403
    assert client.post(
        "/api/v1/pets", headers=write_headers(csrf, origin="https://evil.example"), json=payload
    ).status_code == 403
    assert client.post(
        "/api/v1/pets", headers=write_headers(csrf), json=payload
    ).status_code == 201


def test_csrf_token_endpoint_is_post_only_origin_bound_and_not_cached(auth_runtime):
    new_client, _sessions = auth_runtime
    client = new_client()
    login(client, "alice@example.test")
    assert client.get("/api/v1/auth/csrf", headers={"Origin": ORIGIN}).status_code == 405
    assert client.post("/api/v1/auth/csrf").status_code == 403
    assert client.post("/api/v1/auth/csrf", headers={"Origin": "https://evil.example"}).status_code == 403
    response = client.post("/api/v1/auth/csrf", headers={"Origin": ORIGIN})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/v1/auth/session").headers["cache-control"] == "no-store"


def test_two_users_cannot_cross_pet_episode_plan_or_lists(auth_runtime):
    new_client, _sessions = auth_runtime
    alice = new_client()
    bob = new_client()
    alice_csrf = login(alice, "alice@example.test")
    bob_csrf = login(bob, "bob@example.test")

    pet = alice.post(
        "/api/v1/pets",
        headers=write_headers(alice_csrf),
        json={"name": "Alice pet", "species": "cat"},
    ).json()
    episode = alice.post(
        "/api/v1/episodes/complete",
        headers=write_headers(alice_csrf),
        json={
            "pet_id": pet["id"],
            "happened_at": "2026-10-20T08:00:00Z",
            "episode_type": "resting_behavior",
            "raw_owner_input": "Rested beside the window.",
            "observations": [{
                "behavior_type": "resting_behavior",
                "description": "Lay on the left side for ten minutes.",
                "source_type": "owner_direct",
            }],
            "owner_interpretations": [],
            "safety_check": {
                "result": "NORMAL", "danger_signals": [],
                "acknowledged_at": "2026-10-20T08:01:00Z",
            },
        },
    ).json()
    plan_response = alice.post(
        f"/api/v1/pets/{pet['id']}/observation-plans",
        headers=write_headers(alice_csrf),
        json={
            "status": "DRAFT",
            "start_at": "2026-10-20T08:00:00Z",
            "end_at": "2026-10-21T08:00:00Z",
            "goal": "Observe resting position",
            "items": [{"label": "Position", "is_required": True}],
        },
    )
    assert plan_response.status_code == 201, plan_response.text
    plan = plan_response.json()

    assert bob.get(f"/api/v1/pets/{pet['id']}").status_code == 404
    assert bob.get(f"/api/v1/episodes/{episode['id']}").status_code == 404
    assert bob.get(f"/api/v1/observation-plans/{plan['id']}").status_code == 404
    assert bob.get("/api/v1/pets").json() == []
    assert bob.post(
        "/api/v1/episodes",
        headers=write_headers(bob_csrf),
        json={
            "pet_id": pet["id"],
            "happened_at": "2026-10-20T09:00:00Z",
            "episode_type": "attempt",
            "raw_owner_input": "Must not be written",
        },
    ).status_code == 404
    assert alice.get(f"/api/v1/pets/{pet['id']}/timeline").json()["total"] == 1


def test_nested_resource_idor_matrix_returns_404_without_mutation(auth_runtime):
    new_client, sessions = auth_runtime
    alice = new_client(); bob = new_client()
    alice_csrf = login(alice, "alice@example.test"); bob_csrf = login(bob, "bob@example.test")
    pet = alice.post(
        "/api/v1/pets", headers=write_headers(alice_csrf),
        json={"name": "Alice pet", "species": "cat", "owner_user_id": "attacker-value"},
    ).json()
    episode = alice.post(
        "/api/v1/episodes/complete", headers=write_headers(alice_csrf),
        json={
            "pet_id": pet["id"], "happened_at": "2026-10-20T08:00:00Z",
            "episode_type": "daily_observation", "raw_owner_input": "A private note.",
            "observations": [{"behavior_type": "resting", "description": "Rested ten minutes.", "source_type": "owner_direct"}],
            "owner_interpretations": [{"interpretation": "Owner interpretation."}],
            "safety_check": {"result": "NORMAL", "danger_signals": [], "acknowledged_at": "2026-10-20T08:01:00Z"},
        },
    ).json()
    escalation = alice.post(
        f"/api/v1/episodes/{episode['id']}/veterinary-escalations",
        headers=write_headers(alice_csrf), json={"reason": "Owner-requested review", "status": "OPEN"},
    ).json()
    follow_up = alice.post(
        f"/api/v1/episodes/{episode['id']}/follow-ups",
        headers=write_headers(alice_csrf), json={"scheduled_at": "2099-01-01T00:00:00Z"},
    ).json()
    snapshot_response = alice.post(
        f"/api/v1/pets/{pet['id']}/baseline-snapshots/recompute",
        headers=write_headers(alice_csrf), json={"window": "7d", "as_of": "2026-10-20T12:00:00Z"},
    )
    assert snapshot_response.status_code == 201, snapshot_response.text
    snapshot = snapshot_response.json()

    with sessions() as db:
        source = db.get(Episode, episode["id"]); assert source is not None
        run = AnalysisRun(
            episode_id=source.id, request_id="idor-fixture", status="COMPLETED",
            adapter_name="test", model_provider="test", model_name="test", model_version="v1",
            prompt_contract_version="v1", input_contract_version="v1", output_contract_version="v1",
            input_snapshot={}, normalized_output={}, source_episode_updated_at=source.updated_at,
            completed_at=datetime.now(UTC),
        )
        db.add(run); db.flush()
        claim = Claim(
            analysis_run_id=run.id, claim_type="POSSIBLE_EXPLANATION", statement="Private candidate",
            confidence_label="LOW", status="PROPOSED",
        )
        db.add(claim); db.flush()
        candidate = MemoryCandidate(
            pet_id=pet["id"], claim_id=claim.id, claim_snapshot={}, evidence_snapshot=[],
            uncertainty_snapshot=[], model_snapshot={}, source_episode_updated_at=source.updated_at,
        )
        db.add(candidate); db.commit()
        run_id, claim_id, candidate_id = run.id, claim.id, candidate.id

    probes = [
        bob.get(f"/api/v1/analysis-runs/{run_id}"),
        bob.post(f"/api/v1/claims/{claim_id}/confirmations", headers=write_headers(bob_csrf), json={"decision": "REJECTED"}),
        bob.post(f"/api/v1/claims/{claim_id}/memory-candidate", headers=write_headers(bob_csrf)),
        bob.post(f"/api/v1/memory-candidates/{candidate_id}/decisions", headers=write_headers(bob_csrf), json={"request_id": "attack", "decision": "INCLUDE"}),
        bob.get(f"/api/v1/baseline-snapshots/{snapshot['id']}"),
        bob.post(f"/api/v1/follow-ups/{follow_up['id']}/cancel", headers=write_headers(bob_csrf)),
        bob.patch(f"/api/v1/veterinary-escalations/{escalation['id']}", headers=write_headers(bob_csrf), json={"status": "CLOSED"}),
        bob.get(f"/api/v1/pets/{pet['id']}/memory-candidates"),
        bob.post(
            f"/api/v1/pets/{pet['id']}/memory-candidates/manual",
            headers=write_headers(bob_csrf),
            json={"category": "OTHER", "statement": "Must not be written"},
        ),
        bob.get(f"/api/v1/pets/{pet['id']}/follow-ups"),
        bob.get(f"/api/v1/pets/{pet['id']}/baseline"),
    ]
    assert [item.status_code for item in probes] == [404] * len(probes)

    with sessions() as db:
        assert db.get(Claim, claim_id).status == "PROPOSED"
        assert db.get(MemoryCandidate, candidate_id).decisions == []
        assert db.get(Episode, episode["id"]) is not None
