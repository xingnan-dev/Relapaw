from pathlib import Path

from app.core.config import settings

def episode(client, pet_id):
    return client.post("/api/v1/episodes/complete", json={"pet_id": pet_id, "happened_at": "2026-10-20T08:00:00Z", "episode_type": "observation", "raw_owner_input": "Photo note", "observations": [{"behavior_type": "resting", "description": "Rested on left side", "source_type": "owner_direct"}], "owner_interpretations": [], "safety_check": {"result": "NORMAL", "danger_signals": [], "acknowledged_at": "2026-10-20T08:01:00Z"}}).json()

def test_media_upload_facts_integrity_and_delete(client, pet, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_dir", tmp_path)
    source = episode(client, pet["id"])
    content = b"\x89PNG\r\n\x1a\nsynthetic"
    response = client.post(f"/api/v1/episodes/{source['id']}/media", content=content, headers={"Content-Type": "image/png", "X-Filename": "../pet.png"})
    assert response.status_code == 201
    item = response.json(); assert item["original_filename"] == "pet.png"
    updated = client.patch(f"/api/v1/media/{item['id']}", json={"observable_facts": "Front paws remained on the mat"})
    assert updated.json()["observable_facts"] == "Front paws remained on the mat"
    fetched = client.get(f"/api/v1/media/{item['id']}/content")
    assert fetched.content == content
    assert fetched.headers["x-content-type-options"] == "nosniff"
    stored = next(Path(tmp_path).iterdir()); stored.write_bytes(b"changed")
    assert client.get(f"/api/v1/media/{item['id']}/content").status_code == 409
    assert client.delete(f"/api/v1/media/{item['id']}").status_code == 204
    assert not stored.exists()

def test_media_rejects_type_and_size(client, pet, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_dir", tmp_path); monkeypatch.setattr(settings, "media_max_bytes", 16)
    source = episode(client, pet["id"])
    assert client.post(f"/api/v1/episodes/{source['id']}/media", content=b"x", headers={"Content-Type": "application/octet-stream", "X-Filename": "x.bin"}).status_code == 415
    assert client.post(f"/api/v1/episodes/{source['id']}/media", content=b"1" * 17, headers={"Content-Type": "image/png", "X-Filename": "x.png"}).status_code == 413
    assert client.post(f"/api/v1/episodes/{source['id']}/media", content=b"not png", headers={"Content-Type": "image/png", "X-Filename": "x.png"}).status_code == 415
    assert client.post(f"/api/v1/episodes/{source['id']}/media", content=b"\x89PNG\r\n\x1a\n", headers={"Content-Type": "image/png", "X-Filename": "x.png"}).status_code == 201
