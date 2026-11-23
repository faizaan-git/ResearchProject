
import os
import re
import stat
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from io import BytesIO


# Storage location for uploaded projects
STORAGE_DIR = (
    Path(__file__).resolve().parents[3]
    / "research_storage"
    / "uploaded_projects"
)

# Upload security limits
MAX_ARCHIVE_SIZE = 100 * 1024 * 1024       # 100 MB
MAX_EXTRACTED_SIZE = 500 * 1024 * 1024     # 500 MB
MAX_FILES = 10000
MAX_COMPRESSION_RATIO = 200


def extract_project_zip(
    zip_bytes: bytes,
    original_filename: str
) -> dict:

    # 1. Validate uploaded file
    if not original_filename.lower().endswith(".zip"):
        raise ValueError("Only ZIP files are supported.")

    if not zip_bytes:
        raise ValueError("The uploaded ZIP file is empty.")

    if len(zip_bytes) > MAX_ARCHIVE_SIZE:
        raise ValueError("ZIP file exceeds the 100 MB upload limit.")

    # 2. Create a unique project directory
    project_id = str(uuid.uuid4())
    project_dir = STORAGE_DIR / project_id

    try:
        with zipfile.ZipFile(BytesIO(zip_bytes), "r") as archive:

            entries = archive.infolist()

            if len(entries) > MAX_FILES:
                raise ValueError("ZIP contains too many files.")

            total_size = sum(entry.file_size for entry in entries)

            if total_size > MAX_EXTRACTED_SIZE:
                raise ValueError(
                    "Extracted project exceeds the 500 MB limit."
                )

            # 3. Check archive contents before extracting
            for entry in entries:

                normalized_name = entry.filename.replace("\\", "/")
                archive_path = PurePosixPath(normalized_name)

                if (
                    archive_path.is_absolute()
                    or ".." in archive_path.parts
                    or re.match(r"^[a-zA-Z]:", normalized_name)
                ):
                    raise ValueError(
                        "ZIP contains an unsafe file path."
                    )

                # Skip symbolic links for security
                file_mode = entry.external_attr >> 16

                if stat.S_ISLNK(file_mode):
                    continue


                # Reject encrypted files
                if entry.flag_bits & 0x1:
                    raise ValueError(
                        "Password-protected ZIP files are not supported."
                    )

                if entry.file_size > 0:
                    ratio = entry.file_size / max(entry.compress_size, 1)

                    if ratio > MAX_COMPRESSION_RATIO:
                        raise ValueError(
                            "ZIP contains a suspiciously compressed file."
                        )

            # 4. Extract files safely
            project_dir.mkdir(parents=True, exist_ok=False)

            extracted_files = []

            for entry in entries:

                normalized_name = entry.filename.replace("\\", "/")
                destination = project_dir.joinpath(*PurePosixPath(
                    normalized_name
                ).parts)

                resolved_destination = destination.resolve()
                resolved_root = project_dir.resolve()

                if (
                    resolved_destination != resolved_root
                    and resolved_root not in resolved_destination.parents
                ):
                    raise ValueError(
                        "ZIP attempted to write outside the project directory."
                    )

                if entry.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue

                destination.parent.mkdir(parents=True, exist_ok=True)

                with archive.open(entry, "r") as source:
                    with open(destination, "wb") as target:
                        while True:
                            chunk = source.read(1024 * 1024)

                            if not chunk:
                                break

                            target.write(chunk)

                extracted_files.append(
                    str(destination.relative_to(project_dir))
                )

        return {
            "success": True,
            "project_id": project_id,
            "project_directory": str(project_dir),
            "total_files": len(extracted_files),
            "extracted_files": extracted_files,
            "message": "Project ZIP extracted successfully."
        }

    except Exception:
        # Remove incomplete extraction if anything fails
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir, ignore_errors=True)

        raise
