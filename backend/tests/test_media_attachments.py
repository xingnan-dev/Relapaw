from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import MediaAttachment, MediaAttachmentRevision

def episode(client, pet_id):
    return client.post("/api/v1/episodes/complete", json={"pet_id": pet_id, "happened_at": "2026-10-20T08:00:00Z", "episode_type": "observation", "raw_owner_input": "Photo note", "observations": [{"behavior_type": "resting", "description": "Rested on left side", "source_type": "owner_direct"}], "owner_interpretations": [], "safety_check": {"result": "NORMAL", "danger_signals": [], "acknowledged_at": "2026-10-20T08:01:00Z"}}).json()

def test_media_upload_facts_integrity_and_delete(client, pet, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_dir", tmp_path)
    source = episode(client, pet["id"])
    content = b"\x89PNG\r\n\x1a\nsynthetic"
    response = client.post(f"/api/v1/episodes/{source['id']}/media", content=content, headers={"Content-Type": "image/png", "X-Filename": "../pet.png"})
    assert response.status_code == 201
    item = response.json(); assert item["original_filename"] == "pet.png"
    assert item["pet_id"] == pet["id"]
    assert item["episode_id"] == source["id"]
    assert item["life_event_id"] is None and item["relationship_event_id"] is None
    assert item["revisions"][0]["change_summary"] == "上传附件"
    updated = client.patch(f"/api/v1/media/{item['id']}", json={"observable_facts": "Front paws remained on the mat"})
    assert updated.json()["observable_facts"] == "Front paws remained on the mat"
    fetched = client.get(f"/api/v1/media/{item['id']}/content")
    assert fetched.content == content
    assert fetched.headers["x-content-type-options"] == "nosniff"
    stored = next(Path(tmp_path).iterdir()); stored.write_bytes(b"changed")
    assert client.get(f"/api/v1/media/{item['id']}/content").status_code == 409
    assert client.delete(f"/api/v1/media/{item['id']}").status_code == 204
    assert not stored.exists()


def test_media_accepts_percent_encoded_unicode_filename(client, pet, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_dir", tmp_path)
    source = episode(client, pet["id"])
    response = client.post(
        f"/api/v1/episodes/{source['id']}/media",
        content=b"\x89PNG\r\n\x1a\nsynthetic",
        headers={"Content-Type": "image/png", "X-Filename": "%E5%96%9C%E5%96%9C%E6%95%A3%E6%AD%A5.png"},
    )
    assert response.status_code == 201
    assert response.json()["original_filename"] == "喜喜散步.png"

def test_media_metadata_candidate_and_concrete_life_relationship_sources(client, pet, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_dir", tmp_path)
    life = client.post(f"/api/v1/pets/{pet['id']}/life-events", json={"event_type": "moving", "happened_at": "2026-10-01T08:00:00Z", "description": "Moved the bed"}).json()
    relationship = client.post("/api/v1/relationship-events", json={"relationship_kind": "OWNER_PET", "participant_pet_ids": [pet["id"]], "happened_at": "2026-10-02T08:00:00Z", "observation_type": "OWNER_INTERACTION", "observation_text": "Walked toward me"}).json()
    content = b"\x89PNG\r\n\x1a\nsource"
    life_media = client.post(f"/api/v1/life-events/{life['id']}/media", content=content, headers={"Content-Type": "image/png", "X-Filename": "life.png"})
    assert life_media.status_code == 201, life_media.text
    assert life_media.json()["life_event_id"] == life["id"]
    relation_media = client.post(f"/api/v1/relationship-events/{relationship['id']}/media", content=content, headers={"Content-Type": "image/png", "X-Filename": "relation.png", "X-Pet-ID": str(pet["id"])})
    assert relation_media.status_code == 201, relation_media.text
    item = relation_media.json(); assert item["relationship_event_id"] == relationship["id"]
    updated = client.patch(f"/api/v1/media/{item['id']}/metadata", json={"captured_at": "2026-09-30T10:00:00Z", "owner_caption": "前爪停在门槛内侧。", "change_summary": "补充拍摄时间与原始说明"})
    assert updated.status_code == 200
    assert updated.json()["owner_caption"] == "前爪停在门槛内侧。"
    assert len(updated.json()["revisions"]) == 2
    public_proposal = client.patch(f"/api/v1/media/{item['id']}/candidate", json={"action": "PROPOSE", "ai_candidate_observation": "候选：身体朝向门内。"})
    assert public_proposal.status_code == 422
    with Session(client.app.state.test_engine, expire_on_commit=False) as db:
        stored = db.get(MediaAttachment, item["id"]); assert stored is not None
        stored.ai_candidate_observation = "候选：身体朝向门内。"; stored.ai_candidate_status = "PENDING"; stored.updated_at = datetime.now(timezone.utc)
        db.add(MediaAttachmentRevision(attachment_id=stored.id, revision_number=3, captured_at=stored.captured_at, owner_caption=stored.owner_caption, ai_candidate_observation=stored.ai_candidate_observation, ai_candidate_status=stored.ai_candidate_status, change_summary="服务端受控模型候选"))
        db.commit()
    confirmed = client.patch(f"/api/v1/media/{item['id']}/candidate", json={"action": "CONFIRM"})
    assert confirmed.json()["ai_candidate_status"] == "CONFIRMED"
    assert len(confirmed.json()["revisions"]) == 4
    assert len(client.get(f"/api/v1/life-events/{life['id']}/media").json()) == 1
    assert len(client.get(f"/api/v1/relationship-events/{relationship['id']}/media").json()) == 1
    assert len(list(Path(tmp_path).iterdir())) == 2
    assert client.delete(f"/api/v1/life-events/{life['id']}").status_code == 204
    assert len(list(Path(tmp_path).iterdir())) == 1
    assert client.delete(f"/api/v1/relationship-events/{relationship['id']}").status_code == 204
    assert list(Path(tmp_path).iterdir()) == []

def test_video_duration_and_account_capacity_are_enforced(client, pet, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_dir", tmp_path)
    monkeypatch.setattr(settings, "media_total_bytes_per_user", 20)
    monkeypatch.setattr(settings, "media_max_video_seconds", 10)
    source = episode(client, pet["id"])
    video = b"\x00\x00\x00\x18ftypisom"
    missing = client.post(f"/api/v1/episodes/{source['id']}/media", content=video, headers={"Content-Type": "video/mp4", "X-Filename": "clip.mp4"})
    assert missing.status_code == 422
    too_long = client.post(f"/api/v1/episodes/{source['id']}/media", content=video, headers={"Content-Type": "video/mp4", "X-Filename": "clip.mp4", "X-Media-Duration-Seconds": "11"})
    assert too_long.status_code == 413
    accepted = client.post(f"/api/v1/episodes/{source['id']}/media", content=video, headers={"Content-Type": "video/mp4", "X-Filename": "clip.mp4", "X-Media-Duration-Seconds": "8"})
    assert accepted.status_code == 201
    assert accepted.json()["duration_seconds"] == 8
    capacity = client.post(f"/api/v1/episodes/{source['id']}/media", content=b"\x89PNG\r\n\x1a\nextra", headers={"Content-Type": "image/png", "X-Filename": "extra.png"})
    assert capacity.status_code == 413
    assert capacity.json()["error"]["code"] == "MEDIA_CAPACITY_EXCEEDED"

def test_media_rejects_type_and_size(client, pet, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_dir", tmp_path); monkeypatch.setattr(settings, "media_max_bytes", 16)
    source = episode(client, pet["id"])
    assert client.post(f"/api/v1/episodes/{source['id']}/media", content=b"x", headers={"Content-Type": "application/octet-stream", "X-Filename": "x.bin"}).status_code == 415
    assert client.post(f"/api/v1/episodes/{source['id']}/media", content=b"1" * 17, headers={"Content-Type": "image/png", "X-Filename": "x.png"}).status_code == 413
    assert client.post(f"/api/v1/episodes/{source['id']}/media", content=b"not png", headers={"Content-Type": "image/png", "X-Filename": "x.png"}).status_code == 415
    assert client.post(f"/api/v1/episodes/{source['id']}/media", content=b"\x89PNG\r\n\x1a\n", headers={"Content-Type": "image/png", "X-Filename": "x.png"}).status_code == 201
