import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "demo.ps1"
GUIDE = ROOT / "docs" / "DEMO_OPERATOR_GUIDE.md"


def test_launcher_is_valid_powershell():
    command = (
        "$source = Get-Content -LiteralPath '"
        + str(SCRIPT).replace("'", "''")
        + "' -Raw; [void][scriptblock]::Create($source)"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_launcher_keeps_destructive_scope_literal_and_non_recursive():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "[ValidateSet('start', 'verify', 'reset', 'stop')]" in source
    assert "Remove-Item -LiteralPath $resolved -Force" in source
    assert "Remove-Item -Recurse" not in source
    assert "127.0.0.1" in source
    assert "--reload" not in source
    for allowed in (
        "relapaw-demo.db",
        "manifest.json",
        "server.pid.json",
        "server.stdout.log",
        "server.stderr.log",
    ):
        assert allowed in source


def test_operator_guide_documents_every_command_and_safety_boundary():
    guide = GUIDE.read_text(encoding="utf-8")
    for action in ("start", "verify", "reset", "stop"):
        assert f".\\scripts\\demo.ps1 {action}" in guide
    assert "127.0.0.1" in guide
    assert "不会终止占用进程" in guide
    assert "不需要账号、邮箱、OTP" in guide
