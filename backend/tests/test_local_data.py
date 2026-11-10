import sqlite3
from contextlib import closing
from hashlib import sha256

import pytest

from app import local_data

def test_backup_restore_round_trip_is_consistent_and_rejects_unsafe_archive(tmp_path, monkeypatch):
    backend = tmp_path / "backend"; backend.mkdir()
    database, media, backups = backend / "relapaw.db", backend / "relapaw_media", backend / ".local-backups"
    with closing(sqlite3.connect(database)) as db:
        db.execute("CREATE TABLE alembic_version (version_num TEXT NOT NULL)"); db.execute("INSERT INTO alembic_version VALUES ('test')")
        db.execute("CREATE TABLE facts (value TEXT)"); db.execute("INSERT INTO facts VALUES ('before')")
        db.execute("CREATE TABLE media_attachments (storage_key TEXT, sha256 TEXT, byte_size INTEGER, status TEXT)")
        db.execute("INSERT INTO media_attachments VALUES (?, ?, ?, 'AVAILABLE')", ("a" * 32, __import__('hashlib').sha256(b"media-before").hexdigest(), len(b"media-before")))
        db.commit()
    media.mkdir(); key = "a" * 32; (media / key).write_bytes(b"media-before")
    monkeypatch.setattr(local_data, "BACKEND", backend); monkeypatch.setattr(local_data, "DATABASE", database); monkeypatch.setattr(local_data, "MEDIA", media); monkeypatch.setattr(local_data, "BACKUPS", backups)
    archive = local_data.backup("roundtrip.zip")
    with closing(sqlite3.connect(database)) as db: db.execute("UPDATE facts SET value='after'"); db.commit()
    (media / key).write_bytes(b"media-after")
    local_data.restore(archive.name)
    with closing(sqlite3.connect(database)) as db: assert db.execute("SELECT value FROM facts").fetchone()[0] == "before"
    assert (media / key).read_bytes() == b"media-before"
    try: local_data.archive_path("../outside.zip")
    except RuntimeError: pass
    else: raise AssertionError("unsafe archive path accepted")


@pytest.mark.parametrize("has_avatar", [False, True])
def test_restore_without_record_attachments_keeps_avatar_if_present(tmp_path, monkeypatch, has_avatar):
    database = tmp_path / "relapaw.db"
    media = tmp_path / "relapaw_media"
    for setting, path in {
        "BACKEND": tmp_path, "DATABASE": database, "MEDIA": media, "BACKUPS": tmp_path / ".local-backups",
    }.items():
        monkeypatch.setattr(local_data, setting, path)
    avatar = b"synthetic avatar bytes"
    avatar_key = "avatar-" + "b" * 32
    with closing(sqlite3.connect(database)) as db:
        db.executescript("""
            CREATE TABLE alembic_version (version_num TEXT NOT NULL);
            INSERT INTO alembic_version VALUES ('20261026_0027');
            CREATE TABLE media_attachments (storage_key TEXT, sha256 TEXT, byte_size INTEGER, status TEXT);
            CREATE TABLE pet_avatars (storage_key TEXT, sha256 TEXT, byte_size INTEGER);
        """)
        if has_avatar:
            db.execute("INSERT INTO pet_avatars VALUES (?, ?, ?)", (avatar_key, sha256(avatar).hexdigest(), len(avatar)))
        db.commit()
    if has_avatar:
        media.mkdir()
        (media / avatar_key).write_bytes(avatar)

    archive = local_data.backup("without-record-attachments.zip")
    if has_avatar:
        (media / avatar_key).unlink()
    local_data.restore(archive.name)

    assert media.is_dir()
    assert sorted(path.name for path in media.iterdir()) == ([avatar_key] if has_avatar else [])
    if has_avatar:
        assert (media / avatar_key).read_bytes() == avatar
