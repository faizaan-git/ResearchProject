
import httpx
import shutil

from pathlib import Path
from urllib.parse import urlsplit, quote

from app.project_ingestion.zip_handler import extract_project_zip


# ============================================================
# CONFIGURATION
# ============================================================

MAX_GITHUB_ARCHIVE_SIZE = 100 * 1024 * 1024  # 100 MB
DOWNLOAD_TIMEOUT = 60.0

GITHUB_API_BASE = "https://api.github.com"

GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "ProjectResearch"
}


# ============================================================
# 1. VALIDATE GITHUB REPOSITORY URL
# ============================================================

def validate_github_url(repository_url: str) -> dict:
    """
    Validate a public GitHub repository URL.

    Supported:
        https://github.com/username/repository
        https://github.com/username/repository.git
    """

    if not isinstance(repository_url, str) or not repository_url.strip():
        raise ValueError("Please provide a GitHub repository URL.")

    try:
        parsed = urlsplit(repository_url.strip())

        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or parsed.port is not None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "Only HTTPS GitHub repository URLs are supported."
            )

    except ValueError:
        raise ValueError("Invalid GitHub repository URL.")

    parts = [
        part for part in parsed.path.strip("/").split("/")
        if part
    ]

    if len(parts) != 2:
        raise ValueError(
            "Use this format: "
            "https://github.com/username/repository"
        )

    owner, repository = parts

    if repository.lower().endswith(".git"):
        repository = repository[:-4]

    if not owner or not repository:
        raise ValueError("Invalid GitHub repository details.")

    return {
        "owner": owner,
        "repository": repository,
        "repository_url": (
            f"https://github.com/{owner}/{repository}"
        )
    }


# ============================================================
# 2. DOWNLOAD GITHUB REPOSITORY
# ============================================================

def download_github_repository(
    owner: str,
    repository: str
) -> bytes:
    """
    Download a public GitHub repository as a ZIP archive.

    Enforces a maximum download size of 100 MB.
    """

    owner = quote(owner, safe="")
    repository = quote(repository, safe="")

    download_url = (
        f"{GITHUB_API_BASE}/repos/"
        f"{owner}/{repository}/zipball"
    )

    archive_chunks = []
    downloaded_size = 0

    try:
        with httpx.Client(
            timeout=DOWNLOAD_TIMEOUT,
            follow_redirects=True
        ) as client:

            with client.stream(
                "GET",
                download_url,
                headers=GITHUB_HEADERS
            ) as response:

                response.raise_for_status()

                # Ensure the final download is from GitHub.
                if response.url.host != "codeload.github.com":
                    raise ValueError(
                        "Unexpected GitHub download location."
                    )

                content_length = response.headers.get(
                    "content-length"
                )

                if content_length:
                    try:
                        declared_size = int(content_length)
                    except ValueError:
                        raise ValueError(
                            "GitHub returned an invalid archive size."
                        )

                    if declared_size > MAX_GITHUB_ARCHIVE_SIZE:
                        raise ValueError(
                            "Repository exceeds the 100 MB download limit."
                        )

                for chunk in response.iter_bytes(
                    chunk_size=1024 * 1024
                ):

                    downloaded_size += len(chunk)

                    if downloaded_size > MAX_GITHUB_ARCHIVE_SIZE:
                        raise ValueError(
                            "Repository exceeds the 100 MB download limit."
                        )

                    archive_chunks.append(chunk)

    except httpx.HTTPStatusError as error:

        status_code = error.response.status_code

        if status_code == 404:
            raise ValueError(
                "Repository not found or repository is private."
            )

        if status_code == 403:
            raise ValueError(
                "GitHub access denied or API rate limit exceeded."
            )

        raise ValueError(
            f"GitHub download failed. HTTP status: {status_code}"
        )

    except httpx.TimeoutException:
        raise ValueError("GitHub download timed out.")

    except httpx.RequestError:
        raise ValueError(
            "Unable to connect to GitHub. Check your internet connection."
        )

    archive_bytes = b"".join(archive_chunks)

    if not archive_bytes:
        raise ValueError("GitHub returned an empty repository archive.")

    return archive_bytes


# ============================================================
# 3. NORMALIZE EXTRACTED PROJECT DIRECTORY
# ============================================================

def normalize_project_directory(project_directory: str) -> None:
    """
    Remove GitHub's extra top-level archive directory.

    GitHub ZIP archives generally contain:
        repository-branch/
            README.md
            package.json
            src/

    This function moves the repository contents into the
    project root so existing scanners can analyze them.
    """

    project_root = Path(project_directory).resolve()

    if not project_root.exists() or not project_root.is_dir():
        raise ValueError("Extracted project directory does not exist.")

    entries = list(project_root.iterdir())

    if (
        len(entries) != 1
        or not entries[0].is_dir()
        or entries[0].is_symlink()
    ):
        return

    nested_directory = entries[0]

    for item in nested_directory.iterdir():

        if item.is_symlink():
            raise ValueError(
                "GitHub repository contains an unsupported symbolic link."
            )

        destination = project_root / item.name

        if destination.exists():
            raise ValueError(
                "Repository contains conflicting archive paths."
            )

        shutil.move(str(item), str(destination))

    nested_directory.rmdir()


# ============================================================
# 4. INGEST GITHUB REPOSITORY
# ============================================================

def ingest_github_repository(repository_url: str) -> dict:
    """
    Complete GitHub repository ingestion workflow.

    1. Validate repository URL.
    2. Download repository ZIP.
    3. Extract using the existing secure ZIP handler.
    4. Normalize repository directory.
    5. Return project metadata.

    Project scanning and code analysis are performed
    separately by the FastAPI endpoint.
    """

    repository_info = validate_github_url(repository_url)

    archive_bytes = download_github_repository(
        owner=repository_info["owner"],
        repository=repository_info["repository"]
    )

    upload_result = extract_project_zip(
        zip_bytes=archive_bytes,
        original_filename=(
            f"{repository_info['repository']}.zip"
        )
    )

    project_directory = upload_result["project_directory"]

    try:
        normalize_project_directory(project_directory)

        project_root = Path(project_directory)

        extracted_files = [
            str(path.relative_to(project_root)).replace("\\", "/")
            for path in project_root.rglob("*")
            if path.is_file()
        ]

        upload_result["extracted_files"] = sorted(extracted_files)
        upload_result["total_files"] = len(extracted_files)

    except Exception:
        shutil.rmtree(project_directory, ignore_errors=True)
        raise

    return {
        "success": True,
        "source_type": "github",
        "repository_url": repository_info["repository_url"],
        "repository_owner": repository_info["owner"],
        "repository_name": repository_info["repository"],
        "upload": upload_result,
        "message": (
            "GitHub repository downloaded and extracted successfully."
        )
    }
