"""Consistent local SQLite and media backup with validated atomic restore."""
import argparse, hashlib, json, os, re, shutil, sqlite3, tempfile, zipfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from app.services.media_storage import retry_pending

BACKEND = Path(__file__).resolve().parents[1]
DATABASE, MEDIA, BACKUPS = BACKEND / "relapaw.db", BACKEND / "relapaw_media", BACKEND / ".local-backups"
MEDIA_NAME = re.compile(r"[0-9a-f]{32}")

def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): value.update(chunk)
    return value.hexdigest()

def check_db(path: Path) -> None:
    with closing(sqlite3.connect(path)) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok": raise RuntimeError("SQLite integrity check failed")
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'").fetchone(): raise RuntimeError("Migration table missing")

def archive_path(name: str | None) -> Path:
    BACKUPS.mkdir(exist_ok=True)
    if BACKUPS.is_symlink() or BACKUPS.resolve().parent != BACKEND.resolve(): raise RuntimeError("Unsafe backup directory")
    path = BACKUPS / (name or f"relapaw-local-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip")
    if path.parent.resolve() != BACKUPS.resolve() or path.suffix.lower() != ".zip" or path.is_symlink(): raise RuntimeError("Archive must be a normal .zip directly inside the backup directory")
    return path

def backup(name: str | None) -> Path:
    target = archive_path(name)
    if target.exists(): raise RuntimeError("Backup already exists")
    if not DATABASE.is_file(): raise RuntimeError("Local database does not exist")
    with tempfile.TemporaryDirectory(dir=BACKUPS) as raw:
        stage = Path(raw); snapshot = stage / "relapaw.db"
        with closing(sqlite3.connect(DATABASE)) as source, closing(sqlite3.connect(snapshot)) as destination: source.backup(destination)
        check_db(snapshot); media_stage = stage / "media"; media_stage.mkdir(); files = []
        retry_pending(MEDIA)
        with closing(sqlite3.connect(snapshot)) as db:
            rows = db.execute("SELECT storage_key, sha256, byte_size FROM media_attachments WHERE status = 'AVAILABLE'").fetchall()
        if MEDIA.exists():
            if MEDIA.is_symlink(): raise RuntimeError("Unsafe media directory")
            for key, expected_hash, expected_size in rows:
                if not MEDIA_NAME.fullmatch(key): raise RuntimeError("Invalid media storage key in database")
                source = MEDIA / key
                if source.is_symlink() or not source.is_file() or source.stat().st_size != expected_size or digest(source) != expected_hash: raise RuntimeError("Media does not match the database snapshot")
                destination = media_stage / key; shutil.copy2(source, destination)
                if destination.stat().st_size != expected_size or digest(destination) != expected_hash: raise RuntimeError("Media changed during backup")
                files.append({"path": f"media/{key}", "sha256": expected_hash, "size": expected_size})
        elif rows: raise RuntimeError("Database references media but media directory is missing")
        manifest = {"format": "relapaw-local-backup/v1", "created_at": datetime.now(UTC).isoformat(), "database": {"path": "relapaw.db", "sha256": digest(snapshot), "size": snapshot.stat().st_size}, "media": files}
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(stage / "manifest.json", "manifest.json"); archive.write(snapshot, "relapaw.db")
            for item in files: archive.write(stage / item["path"], item["path"])
    return target

def restore(name: str) -> Path:
    source = archive_path(name)
    if not source.is_file(): raise RuntimeError("Backup not found")
    with tempfile.TemporaryDirectory(dir=BACKUPS) as raw:
        stage = Path(raw); total = 0
        with zipfile.ZipFile(source) as archive:
            entries = archive.infolist()
            if len(entries) > 10002: raise RuntimeError("Archive contains too many files")
            for entry in entries:
                pure = PurePosixPath(entry.filename); total += entry.file_size
                allowed = entry.filename in {"manifest.json", "relapaw.db"} or (len(pure.parts) == 2 and pure.parts[0] == "media" and MEDIA_NAME.fullmatch(pure.parts[1]))
                if not allowed or pure.is_absolute() or ".." in pure.parts or total > 1024 * 1024 * 1024: raise RuntimeError("Unsafe archive contents")
                destination = stage.joinpath(*pure.parts); destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as incoming, destination.open("xb") as outgoing: shutil.copyfileobj(incoming, outgoing)
        manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("format") != "relapaw-local-backup/v1": raise RuntimeError("Unsupported backup format")
        for item in [manifest["database"], *manifest.get("media", [])]:
            path = stage.joinpath(*PurePosixPath(item["path"]).parts)
            if not path.is_file() or path.stat().st_size != item["size"] or digest(path) != item["sha256"]: raise RuntimeError("Backup checksum validation failed")
        check_db(stage / "relapaw.db")
        rollback = Path(tempfile.mkdtemp(prefix=".restore-rollback-", dir=BACKEND)); old_db, old_media = rollback / "relapaw.db", rollback / "relapaw_media"
        old_db_moved = old_media_moved = new_db_installed = new_media_installed = False
        restore_succeeded = False
        try:
            if DATABASE.exists(): os.replace(DATABASE, old_db); old_db_moved = True
            if MEDIA.exists(): os.replace(MEDIA, old_media); old_media_moved = True
            os.replace(stage / "relapaw.db", DATABASE); new_db_installed = True
            os.replace(stage / "media", MEDIA); new_media_installed = True
        except Exception:
            rollback_error = None
            try:
                if new_db_installed and DATABASE.exists(): DATABASE.unlink()
                if new_media_installed and MEDIA.exists(): shutil.rmtree(MEDIA)
                if old_db_moved and old_db.exists(): os.replace(old_db, DATABASE)
                if old_media_moved and old_media.exists(): os.replace(old_media, MEDIA)
                restore_succeeded = True
            except Exception as error:
                rollback_error = error
            if rollback_error is not None:
                raise RuntimeError(f"Restore failed and rollback data was preserved at {rollback}: {rollback_error}") from rollback_error
            raise
        else: restore_succeeded = True
        finally:
            if restore_succeeded: shutil.rmtree(rollback, ignore_errors=True)
    return source

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("action", choices=("status", "backup", "restore")); parser.add_argument("--archive"); parser.add_argument("--confirm-restore", action="store_true"); args = parser.parse_args()
    if args.action == "status": print(json.dumps({"database": str(DATABASE), "database_exists": DATABASE.is_file(), "media": str(MEDIA), "media_exists": MEDIA.is_dir(), "backup_root": str(BACKUPS)}, indent=2)); return
    if args.action == "backup": print(backup(args.archive)); return
    if not args.confirm_restore or not args.archive: raise RuntimeError("Restore requires --archive and --confirm-restore after stopping Relapaw")
    print(restore(args.archive))

if __name__ == "__main__": main()
