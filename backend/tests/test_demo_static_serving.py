from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def configured_settings(*, environment: str = "development", static_dir: Path | None = None) -> Settings:
    values: dict[str, object] = {
        "RELAPAW_ENV": environment,
        "RELAPAW_AI_ENABLED": False,
    }
    if static_dir is not None:
        values["RELAPAW_STATIC_DIR"] = static_dir
    return Settings(_env_file=None, **values)


def build_frontend(tmp_path: Path) -> Path:
    output = tmp_path / "dist"
    assets = output / "assets"
    assets.mkdir(parents=True)
    (output / "index.html").write_text(
        '<!doctype html><script type="module" src="/assets/main.js"></script><div id="root"></div>',
        encoding="utf-8",
    )
    (assets / "main.js").write_text('document.title = "Relapaw demo";', encoding="utf-8")
    return output.resolve()


def test_development_without_static_dir_remains_api_only():
    with TestClient(create_app(configured_settings())) as client:
        assert client.get("/health").json()["static_frontend"] is False
        assert client.get("/").status_code == 404


def test_demo_serves_index_assets_and_keeps_api_and_health_priority(tmp_path):
    static_dir = build_frontend(tmp_path)
    with TestClient(create_app(
        configured_settings(environment="demo", static_dir=static_dir),
        expected_static_dir=static_dir,
    )) as client:
        root = client.get("/")
        asset = client.get("/assets/main.js")
        health = client.get("/health")
        capabilities = client.get("/api/v1/capabilities")

    assert root.status_code == 200
    assert '<div id="root"></div>' in root.text
    assert asset.status_code == 200
    assert "Relapaw demo" in asset.text
    assert health.status_code == 200
    assert health.json()["static_frontend"] is True
    assert capabilities.status_code == 401


def test_demo_requires_static_dir():
    with pytest.raises(RuntimeError, match="required in demo mode"):
        create_app(configured_settings(environment="demo"))


@pytest.mark.parametrize("case", ["missing", "no-index", "relative"])
def test_invalid_static_build_fails_before_start(tmp_path, case):
    if case == "missing":
        path = (tmp_path / "missing").resolve()
    elif case == "no-index":
        path = (tmp_path / "empty").resolve()
        path.mkdir()
    else:
        path = Path("relative/dist")
    with pytest.raises(RuntimeError, match="RELAPAW_STATIC_DIR"):
        create_app(configured_settings(environment="demo", static_dir=path), expected_static_dir=path)


def test_unknown_api_path_stays_a_404_when_frontend_is_mounted(tmp_path):
    static_dir = build_frontend(tmp_path)
    with TestClient(create_app(
        configured_settings(environment="demo", static_dir=static_dir),
        expected_static_dir=static_dir,
    )) as client:
        response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert "text/html" not in response.headers.get("content-type", "")


def test_demo_rejects_a_valid_but_unexpected_directory(tmp_path):
    static_dir = build_frontend(tmp_path)
    expected = (tmp_path / "repository" / "frontend" / "dist").resolve()
    with pytest.raises(RuntimeError, match="this repository's frontend/dist"):
        create_app(
            configured_settings(environment="demo", static_dir=static_dir),
            expected_static_dir=expected,
        )
