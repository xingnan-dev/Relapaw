from pathlib import Path

import pytest

from app.api.deps import require_current_user
from app.api.routes import pets as pet_routes
from app.main import app
from app.models import User
from app.models import OwnerProfile
from app.services.caregiver_context import consented_caregiver_context


PNG = b"\x89PNG\r\n\x1a\n" + b"safe-test-image"
JPEG = b"\xff\xd8\xff" + b"safe-test-image"
WEBP = b"RIFF\x0e\x00\x00\x00WEBP" + b"safe-test-image"


def test_caregiver_background_is_optional_editable_exportable_and_deletable(client):
    payload = {
        "living_together_since": "2024-01-01",
        "primary_caregiver": "我和家人轮流",
        "household_members": ["一位老人", "一名儿童"],
        "daily_routine": "工作日白天外出",
        "pet_alone_hours": 6,
        "pet_care_experience": "第一次养猫",
        "current_concerns": "最近夜间活动增加",
        "reminder_preference": "每周一次",
        "recording_capacity": "可以每晚简短记录和拍照",
        "household_context": {"children": True, "older_adults": True, "other_pets": False},
        "caregiving_constraints": "工作日上午无法复评",
        "ai_context_enabled": True,
        "ai_context_fields": ["daily_routine", "current_concerns", "recording_capacity"],
    }
    created = client.put("/api/v1/owner-profile", json=payload)
    assert created.status_code == 200
    assert created.json()["ai_context_consent_updated_at"] is not None
    exported = client.get("/api/v1/privacy/export").json()
    assert exported["owner_profiles"][0]["current_concerns"] == payload["current_concerns"]

    withdrawn = client.put("/api/v1/owner-profile", json={**payload, "ai_context_enabled": False, "ai_context_fields": None})
    assert withdrawn.status_code == 200
    assert withdrawn.json()["ai_context_fields"] is None
    assert client.put("/api/v1/owner-profile", json={"ai_context_enabled": False, "ai_context_fields": ["daily_routine"]}).status_code == 422

    assert client.delete("/api/v1/owner-profile").status_code == 204
    assert client.get("/api/v1/owner-profile").status_code == 404


def test_dynamic_pet_profile_and_avatar_lifecycle_are_tenant_scoped(client, tmp_path, monkeypatch):
    monkeypatch.setattr(pet_routes.settings, "media_dir", tmp_path)
    created = client.post("/api/v1/pets", json={
        "name": "Mochi", "species": "cat", "weight_kg": 4.2,
        "known_conditions": ["兽医已确认的慢性情况"],
        "medications": ["处方信息由主人原样记录"], "allergies": ["已知食物过敏"],
        "living_environment": "室内生活，有安静躲藏处",
        "veterinarian_confirmed_facts": [{"fact": "需要定期复查", "confirmed_at": "2026-09-01"}],
        "owner_observations": {"sleep": "常在午后休息", "feeding": "分两次进食"},
    })
    assert created.status_code == 201
    pet_id = created.json()["id"]
    uploaded = client.put(
        f"/api/v1/pets/{pet_id}/avatar",
        content=PNG,
        headers={"Content-Type": "image/png", "X-Filename": "../mochi.png"},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["original_filename"] == "mochi.png"
    assert client.get(f"/api/v1/pets/{pet_id}/avatar/content").content == PNG
    assert client.put(f"/api/v1/pets/{pet_id}/avatar", content=b"not-an-image", headers={"Content-Type": "image/png", "X-Filename": "bad.png"}).status_code == 415
    assert client.get(f"/api/v1/pets/{pet_id}/avatar/content").content == PNG
    assert len(list(Path(tmp_path).glob("avatar-*"))) == 1
    assert not list(Path(tmp_path).glob(".*.uploading"))

    app.dependency_overrides[require_current_user] = lambda: User(id="00000000-0000-0000-0000-000000000099", status="ACTIVE")
    assert client.get(f"/api/v1/pets/{pet_id}/avatar/content").status_code == 404
    assert client.delete(f"/api/v1/pets/{pet_id}/avatar").status_code == 404
    app.dependency_overrides[require_current_user] = lambda: User(id="00000000-0000-0000-0000-000000000001", status="ACTIVE")

    avatar_path = next(Path(tmp_path).glob("avatar-*"))
    assert client.delete(f"/api/v1/pets/{pet_id}/avatar").status_code == 204
    assert not avatar_path.exists()
    assert client.get(f"/api/v1/pets/{pet_id}/avatar/content").status_code == 404


def test_avatar_accepts_percent_encoded_unicode_filename(client, tmp_path, monkeypatch):
    monkeypatch.setattr(pet_routes.settings, "media_dir", tmp_path)
    pet = client.post("/api/v1/pets", json={"name": "Mochi", "species": "cat"}).json()
    response = client.put(
        f"/api/v1/pets/{pet['id']}/avatar",
        content=PNG,
        headers={"Content-Type": "image/png", "X-Filename": "%E5%AE%A0%E7%89%A9%E7%85%A7%E7%89%87.png"},
    )
    assert response.status_code == 200
    assert response.json()["original_filename"] == "宠物照片.png"


@pytest.mark.parametrize(("media_type", "filename", "content"), [
    ("image/jpeg", "pet.jpg", JPEG),
    ("image/png", "pet.png", PNG),
    ("image/webp", "pet.webp", WEBP),
])
def test_avatar_accepts_supported_file_signatures(client, tmp_path, monkeypatch, media_type, filename, content):
    monkeypatch.setattr(pet_routes.settings, "media_dir", tmp_path)
    pet = client.post("/api/v1/pets", json={"name": "Mochi", "species": "cat"}).json()
    response = client.put(f"/api/v1/pets/{pet['id']}/avatar", content=content, headers={"Content-Type": media_type, "X-Filename": filename})
    assert response.status_code == 200
    assert response.json()["media_type"] == media_type


def test_avatar_rejects_unsupported_type_and_oversize_header(client, pet, tmp_path, monkeypatch):
    monkeypatch.setattr(pet_routes.settings, "media_dir", tmp_path)
    pet_id = pet["id"]
    assert client.put(f"/api/v1/pets/{pet_id}/avatar", content=b"GIF89a", headers={"Content-Type": "image/gif", "X-Filename": "x.gif"}).status_code == 415
    monkeypatch.setattr(pet_routes.settings, "avatar_max_bytes", 4)
    assert client.put(f"/api/v1/pets/{pet_id}/avatar", content=PNG, headers={"Content-Type": "image/png", "X-Filename": "x.png"}).status_code == 413


def test_ai_context_uses_only_explicitly_selected_fields_and_stops_after_withdrawal():
    profile = OwnerProfile(
        user_id="owner", daily_routine="白天工作", current_concerns="夜间活动", caregiving_constraints="上午无法复评",
        ai_context_enabled=True, ai_context_fields=["daily_routine", "current_concerns"],
    )
    assert consented_caregiver_context(profile) == {"daily_routine": "白天工作", "current_concerns": "夜间活动"}
    profile.ai_context_enabled = False
    assert consented_caregiver_context(profile) == {}
