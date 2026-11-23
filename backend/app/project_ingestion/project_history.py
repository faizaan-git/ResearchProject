from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import sqlite3
from typing import Any, Iterator
from uuid import uuid4


HISTORY_DB_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "project_history.sqlite3"
)
MAX_RECENT_PROJECTS = 10


@contextmanager
def _database_connection() -> Iterator[sqlite3.Connection]:
    HISTORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(HISTORY_DB_PATH), timeout=10)
    connection.row_factory = sqlite3.Row

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS project_history (
                id TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_filename TEXT NOT NULL,
                analyzed_at TEXT NOT NULL,
                files_scanned INTEGER NOT NULL,
                python_files_scanned INTEGER NOT NULL,
                classes_count INTEGER NOT NULL,
                functions_count INTEGER NOT NULL,
                analysis_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_project_history_analyzed_at
            ON project_history (analyzed_at DESC)
            """
        )
        connection.commit()
        yield connection
        connection.commit()
    finally:
        connection.close()


def _count_list(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    return len(value) if isinstance(value, list) else 0


def _analysis_for_storage(analysis: dict[str, Any]) -> dict[str, Any]:
    stored_analysis = json.loads(json.dumps(analysis, ensure_ascii=False))
    upload = stored_analysis.get("upload")

    if isinstance(upload, dict):
        upload.pop("project_directory", None)
        upload.pop("extracted_files", None)

    return stored_analysis


def save_project_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    stored_analysis = _analysis_for_storage(analysis)
    project = stored_analysis.get("project_analysis") or {}
    code = stored_analysis.get("code_analysis") or {}
    upload = stored_analysis.get("upload") or {}
    source_type = stored_analysis.get("source_type") or (
        "github" if stored_analysis.get("repository_url") else "zip_upload"
    )
    source_url = stored_analysis.get("repository_url") or ""
    source_filename = PurePosixPath(
        str(upload.get("filename") or "").replace("\\", "/")
    ).name
    if source_filename:
        upload["filename"] = source_filename
    project_name = (
        stored_analysis.get("repository_name")
        or project.get("project_name")
        or PurePosixPath(source_filename.replace("\\", "/")).stem
        or "Analyzed project"
    )
    files_scanned = (
        project.get("total_files_scanned")
        if project.get("total_files_scanned") is not None
        else upload.get("total_files", 0)
    )
    analyzed_at = datetime.now(timezone.utc).isoformat()
    project_id = str(uuid4())

    recent_project = {
        "id": project_id,
        "project_name": str(project_name),
        "source_type": str(source_type),
        "repository_url": str(source_url),
        "source_filename": str(source_filename),
        "analyzed_at": analyzed_at,
        "files_scanned": int(files_scanned or 0),
        "python_files_scanned": int(code.get("python_files_scanned") or 0),
        "classes_count": _count_list(code, "classes"),
        "functions_count": _count_list(code, "functions"),
    }
    stored_analysis["project_id"] = project_id

    with _database_connection() as connection:
        connection.execute(
            """
            INSERT INTO project_history (
                id, project_name, source_type, source_url, source_filename,
                analyzed_at, files_scanned, python_files_scanned,
                classes_count, functions_count, analysis_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recent_project["id"],
                recent_project["project_name"],
                recent_project["source_type"],
                recent_project["repository_url"],
                recent_project["source_filename"],
                recent_project["analyzed_at"],
                recent_project["files_scanned"],
                recent_project["python_files_scanned"],
                recent_project["classes_count"],
                recent_project["functions_count"],
                json.dumps(stored_analysis, ensure_ascii=False),
            ),
        )

    return recent_project


def list_recent_projects(limit: int = MAX_RECENT_PROJECTS) -> list[dict[str, Any]]:
    with _database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id, project_name, source_type, source_url AS repository_url,
                source_filename, analyzed_at, files_scanned,
                python_files_scanned, classes_count, functions_count
            FROM project_history
            ORDER BY analyzed_at DESC, rowid DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_project_analysis(project_id: str) -> dict[str, Any] | None:
    with _database_connection() as connection:
        row = connection.execute(
            "SELECT analysis_json FROM project_history WHERE id = ?",
            (project_id,),
        ).fetchone()

    if row is None:
        return None

    analysis = json.loads(row["analysis_json"])
    analysis.setdefault("project_id", project_id)
    return analysis


def delete_project_analysis(project_id: str) -> bool:
    with _database_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM project_history WHERE id = ?",
            (project_id,),
        )

    return cursor.rowcount > 0
