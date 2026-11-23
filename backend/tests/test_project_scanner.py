import json

from app.project_ingestion.project_scanner import scan_project


def test_scan_project_detects_backend_technologies_in_nested_manifests(
    tmp_path,
):
    backend_directory = tmp_path / "backend"
    frontend_directory = tmp_path / "frontend"
    backend_directory.mkdir()
    frontend_directory.mkdir()
    (backend_directory / "requirements.txt").write_text(
        "fastapi==0.1\nuvicorn>=0.2\n",
        encoding="utf-8",
    )
    (backend_directory / "package.json").write_text(
        json.dumps({"dependencies": {"express": "^5.0.0"}}),
        encoding="utf-8",
    )
    (frontend_directory / "package.json").write_text(
        json.dumps({"dependencies": {"react": "^19.0.0"}}),
        encoding="utf-8",
    )

    analysis = scan_project(str(tmp_path))

    assert analysis["backend_technologies"] == [
        "Express.js",
        "FastAPI",
        "Node.js",
        "Python",
        "Uvicorn",
    ]
    assert "React" in analysis["detected_frameworks"]
    assert "React" not in analysis["backend_technologies"]


def test_scan_project_returns_empty_backend_technologies_when_none_detected(
    tmp_path,
):
    (tmp_path / "requirements.txt").write_text(
        "requests==2.0\n",
        encoding="utf-8",
    )

    analysis = scan_project(str(tmp_path))

    assert analysis["backend_technologies"] == []
