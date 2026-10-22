import json
from pathlib import Path

def cleanup_path(path: Path, media_dir: Path) -> None:
    if not path.exists(): return
    try:
        path.unlink(); return
    except OSError: pass
    journal = media_dir / ".cleanup-pending.jsonl"
    with journal.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"name": path.name}) + "\n")

def retry_pending(media_dir: Path) -> None:
    journal = media_dir / ".cleanup-pending.jsonl"
    if not journal.is_file(): return
    remaining = []
    for line in journal.read_text(encoding="utf-8").splitlines():
        try: name = json.loads(line)["name"]
        except (ValueError, KeyError, TypeError): continue
        if "/" in name or "\\" in name: continue
        target = media_dir / name
        try:
            if target.exists(): target.unlink()
        except OSError: remaining.append({"name": name})
    if remaining:
        journal.write_text("".join(json.dumps(item) + "\n" for item in remaining), encoding="utf-8")
    else:
        journal.unlink(missing_ok=True)
