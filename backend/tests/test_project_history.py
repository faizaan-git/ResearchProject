from fastapi.testclient import TestClient

from app import main
from app.project_ingestion import project_history


def test_backend_brand_is_research_ai():
    with TestClient(main.app) as client:
        assert client.get("/").json()["project"] == "ProjectResearch"
        assert client.get("/health").json()["application"] == "ProjectResearch"
        assert client.get("/api/v1/system/info").json()["project"] == "ProjectResearch"


def test_uploaded_project_is_saved_and_can_be_reopened(monkeypatch, tmp_path):
    monkeypatch.setattr(
        project_history,
        "HISTORY_DB_PATH",
        tmp_path / "project_history.sqlite3",
    )
    project_directory = str(tmp_path / "extracted-project")

    def fake_extract_project_zip(zip_bytes, original_filename):
        assert zip_bytes == b"zip-data"
        assert original_filename == "student-project.zip"
        return {
            "project_id": "temporary-id",
            "project_directory": project_directory,
            "total_files": 1,
            "extracted_files": ["app.py"],
        }

    monkeypatch.setattr(main, "extract_project_zip", fake_extract_project_zip)
    monkeypatch.setattr(
        main,
        "scan_project",
        lambda directory: {
            "project_name": "temporary-id",
            "total_files_scanned": 1,
            "skipped_files": 0,
            "programming_languages": [{"language": "Python", "file_count": 1}],
            "dependencies": [],
        },
    )
    monkeypatch.setattr(
        main,
        "analyze_python_project",
        lambda directory: {
            "python_files_scanned": 1,
            "classes": [{"name": "Example"}],
            "functions": [{"name": "run"}],
            "imports": [],
            "api_routes": [],
        },
    )

    with TestClient(main.app) as client:
        upload_response = client.post(
            "/api/v1/projects/upload",
            files={"file": ("student-project.zip", b"zip-data", "application/zip")},
        )

        assert upload_response.status_code == 200
        uploaded_analysis = upload_response.json()["data"]
        assert uploaded_analysis["repository_name"] == "student-project"
        assert uploaded_analysis["source_type"] == "zip_upload"

        recent_response = client.get("/api/v1/projects/recent")
        assert recent_response.status_code == 200
        recent_project = recent_response.json()["data"][0]
        assert recent_project["project_name"] == "student-project"
        assert recent_project["source_filename"] == "student-project.zip"

        reopened_response = client.get(
            f"/api/v1/projects/recent/{recent_project['id']}"
        )
        assert reopened_response.status_code == 200
        reopened_analysis = reopened_response.json()["data"]
        assert reopened_analysis["project_id"] == recent_project["id"]
        assert reopened_analysis["code_analysis"]["classes"][0]["name"] == "Example"
        assert "project_directory" not in reopened_analysis["upload"]
        assert "extracted_files" not in reopened_analysis["upload"]


def test_recent_projects_are_limited_and_unknown_project_returns_404(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        project_history,
        "HISTORY_DB_PATH",
        tmp_path / "project_history.sqlite3",
    )

    for index in range(12):
        project_history.save_project_analysis(
            {
                "source_type": "github",
                "repository_url": f"https://github.com/example/project-{index}",
                "repository_name": f"project-{index}",
                "upload": {},
                "project_analysis": {"total_files_scanned": index},
                "code_analysis": {},
            }
        )

    with TestClient(main.app) as client:
        recent_response = client.get("/api/v1/projects/recent")
        assert recent_response.status_code == 200
        assert len(recent_response.json()["data"]) == 10

        invalid_limit_response = client.get(
            "/api/v1/projects/recent?limit=11"
        )
        assert invalid_limit_response.status_code == 422

        missing_project_response = client.get(
            "/api/v1/projects/recent/not-a-project"
        )
        assert missing_project_response.status_code == 404


def test_github_analysis_is_added_to_recent_projects(monkeypatch, tmp_path):
    monkeypatch.setattr(
        project_history,
        "HISTORY_DB_PATH",
        tmp_path / "project_history.sqlite3",
    )
    monkeypatch.setattr(
        main,
        "ingest_github_repository",
        lambda repository_url: {
            "source_type": "github",
            "repository_url": repository_url,
            "repository_owner": "example",
            "repository_name": "demo-repository",
            "upload": {
                "project_directory": str(tmp_path / "downloaded"),
                "total_files": 2,
            },
        },
    )
    monkeypatch.setattr(
        main,
        "scan_project",
        lambda directory: {"total_files_scanned": 2},
    )
    monkeypatch.setattr(
        main,
        "analyze_python_project",
        lambda directory: {
            "python_files_scanned": 1,
            "classes": [],
            "functions": [],
        },
    )

    with TestClient(main.app) as client:
        analysis_response = client.post(
            "/api/v1/projects/github",
            json={"repository_url": "https://github.com/example/demo-repository"},
        )

        assert analysis_response.status_code == 200
        recent_response = client.get("/api/v1/projects/recent")
        assert recent_response.status_code == 200
        recent_project = recent_response.json()["data"][0]
        assert recent_project["project_name"] == "demo-repository"
        assert recent_project["repository_url"] == (
            "https://github.com/example/demo-repository"
        )


def test_recent_project_can_be_deleted(monkeypatch, tmp_path):
    monkeypatch.setattr(
        project_history,
        "HISTORY_DB_PATH",
        tmp_path / "project_history.sqlite3",
    )
    saved_project = project_history.save_project_analysis(
        {
            "source_type": "github",
            "repository_name": "demo-project",
            "upload": {},
            "project_analysis": {},
            "code_analysis": {},
        }
    )

    with TestClient(main.app) as client:
        delete_response = client.delete(
            f"/api/v1/projects/recent/{saved_project['id']}"
        )

        assert delete_response.status_code == 200
        assert delete_response.json()["data"]["id"] == saved_project["id"]
        assert client.get(
            f"/api/v1/projects/recent/{saved_project['id']}"
        ).status_code == 404
        assert client.get("/api/v1/projects/recent").json()["data"] == []

        missing_delete_response = client.delete(
            f"/api/v1/projects/recent/{saved_project['id']}"
        )
        assert missing_delete_response.status_code == 404


def test_report_generation_routes_are_removed():
    route_paths = {route.path for route in main.app.routes}

    assert "/api/v1/projects/recent/{project_id}/reports" not in route_paths
    assert "/api/v1/reports/recent" not in route_paths
    assert "/api/v1/reports/{report_id}" not in route_paths
