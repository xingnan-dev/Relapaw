import sqlite3
from contextlib import closing
from pathlib import Path
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
