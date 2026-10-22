def test_pet_crud(client):
    created = client.post(
        "/api/v1/pets",
        json={"name": "Mochi", "species": "cat", "approximate_age": "about 2 years"},
    )
    assert created.status_code == 201
    pet_id = created.json()["id"]

    fetched = client.get(f"/api/v1/pets/{pet_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Mochi"

    updated = client.patch(f"/api/v1/pets/{pet_id}", json={"name": "Mochi Bean", "neutered": True})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Mochi Bean"
    assert updated.json()["neutered"] is True


def test_pet_archiving_is_reversible_and_hidden_from_default_list(client):
    created = client.post("/api/v1/pets", json={"name": "Mochi", "species": "cat"})
    pet_id = created.json()["id"]

    archived = client.patch(f"/api/v1/pets/{pet_id}", json={"archived": True})
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert client.get("/api/v1/pets").json() == []
    assert [item["id"] for item in client.get("/api/v1/pets?include_archived=true").json()] == [pet_id]
    assert client.get(f"/api/v1/pets/{pet_id}").status_code == 404
    blocked_record = client.post("/api/v1/episodes", json={
        "pet_id": pet_id,
        "happened_at": "2026-01-01T08:00:00Z",
        "episode_type": "behavior_change",
        "raw_owner_input": "Should not be written while archived",
    })
    assert blocked_record.status_code == 404

    restored = client.patch(f"/api/v1/pets/{pet_id}", json={"archived": False})
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    assert client.get("/api/v1/pets").json()[0]["id"] == pet_id


def test_missing_pet_returns_404(client):
    response = client.get("/api/v1/pets/999")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "PET_NOT_FOUND", "message": "Pet not found", "details": None}
    }


def test_episode_with_invalid_pet_returns_404(client):
    response = client.post(
        "/api/v1/episodes",
        json={
            "pet_id": 999,
            "happened_at": "2026-01-01T08:00:00Z",
            "episode_type": "behavior_change",
            "raw_owner_input": "Something changed",
        },
    )
    assert response.status_code == 404
