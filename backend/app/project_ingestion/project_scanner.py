
import json
import os
from pathlib import Path
from collections import Counter


# Folders that should not be scanned
IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "coverage",
    ".next",
    "vendor"
}

# Files that should not be read
IGNORED_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519"
}

# Extensions mapped to programming languages
LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".go": "Go",
    ".rs": "Rust",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL"
}

# Configuration and dependency files
IMPORTANT_FILES = {
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
    "poetry.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "pom.xml",
    "build.gradle",
    "Cargo.toml",
    "composer.json",
    "Dockerfile",
    "docker-compose.yml",
    "vite.config.js",
    "vite.config.ts",
    "tsconfig.json",
    "README.md",
    "manage.py"
}

# Common framework indicators
FRAMEWORK_INDICATORS = {
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "express": "Express.js",
    "react": "React",
    "react-dom": "React",
    "vue": "Vue.js",
    "angular": "Angular",
    "next": "Next.js",
    "vite": "Vite",
    "tailwindcss": "Tailwind CSS",
    "streamlit": "Streamlit",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "sqlalchemy": "SQLAlchemy",
    "prisma": "Prisma"
}

BACKEND_TECHNOLOGY_INDICATORS = {
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "starlette": "Starlette",
    "uvicorn": "Uvicorn",
    "gunicorn": "Gunicorn",
    "hypercorn": "Hypercorn",
    "express": "Express.js",
    "@nestjs/core": "NestJS",
    "koa": "Koa",
    "@hapi/hapi": "Hapi",
    "spring-boot-starter-web": "Spring Boot",
    "spring-boot-starter-webflux": "Spring WebFlux",
    "laravel/framework": "Laravel",
    "symfony/framework-bundle": "Symfony",
    "sqlalchemy": "SQLAlchemy",
    "prisma": "Prisma"
}

BACKEND_RUNTIME_INDICATORS = {
    "fastapi": "Python",
    "django": "Python",
    "flask": "Python",
    "starlette": "Python",
    "uvicorn": "Python",
    "gunicorn": "Python",
    "hypercorn": "Python",
    "express": "Node.js",
    "@nestjs/core": "Node.js",
    "koa": "Node.js",
    "@hapi/hapi": "Node.js",
    "spring-boot-starter-web": "Java",
    "spring-boot-starter-webflux": "Java",
    "laravel/framework": "PHP",
    "symfony/framework-bundle": "PHP"
}

MAX_FILES_TO_SCAN = 10000
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB per file


def read_dependency_names(project_root: Path) -> set:
    """Read dependency names from supported manifests throughout a project."""

    dependencies = set()

    for current_root, directories, files in os.walk(
        project_root,
        followlinks=False
    ):
        current_path = Path(current_root)
        directories[:] = [
            directory for directory in directories
            if directory not in IGNORED_DIRECTORIES
            and not (current_path / directory).is_symlink()
        ]

        for filename in files:
            manifest = current_path / filename

            if manifest.is_symlink():
                continue

            if filename == "package.json":
                try:
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    for section in ("dependencies", "devDependencies"):
                        dependencies.update(data.get(section, {}).keys())
                except (OSError, json.JSONDecodeError, AttributeError):
                    continue

            elif (
                filename.lower().startswith("requirements")
                and filename.lower().endswith(".txt")
            ):
                try:
                    lines = manifest.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    ).splitlines()
                except OSError:
                    continue

                for line in lines:
                    line = line.strip()

                    if not line or line.startswith(("#", "-")):
                        continue

                    name = line.split(
                        "==", 1
                    )[0].split(
                        ">=", 1
                    )[0].split(
                        "<=", 1
                    )[0].split(
                        "~=", 1
                    )[0].strip()

                    if name:
                        dependencies.add(name)

    return dependencies


def scan_project(project_directory: str) -> dict:
    """Scan a project directory and identify its structure and technologies."""

    root = Path(project_directory).resolve()

    if not root.exists() or not root.is_dir():
        raise ValueError("Project directory does not exist.")

    languages = Counter()
    important_files = []
    file_structure = []
    skipped_files = 0
    scanned_files = 0

    for current_root, directories, files in os.walk(root, followlinks=False):

        # Avoid scanning unnecessary or linked directories
        current_path = Path(current_root)

        directories[:] = [
            directory for directory in directories
            if directory not in IGNORED_DIRECTORIES
            and not (current_path / directory).is_symlink()
        ]

        relative_folder = current_path.relative_to(root)

        file_structure.append(
            str(relative_folder).replace("\\", "/")
            if str(relative_folder) != "."
            else "."
        )

        for filename in files:

            file_path = current_path / filename

            if filename.lower() in IGNORED_FILES:
                skipped_files += 1
                continue

            if file_path.is_symlink():
                skipped_files += 1
                continue

            if file_path.stat().st_size > MAX_FILE_SIZE:
                skipped_files += 1
                continue

            scanned_files += 1

            if scanned_files > MAX_FILES_TO_SCAN:
                raise ValueError(
                    "Project contains too many files to scan."
                )

            extension = file_path.suffix.lower()

            if extension in LANGUAGE_EXTENSIONS:
                languages[LANGUAGE_EXTENSIONS[extension]] += 1

            if filename in IMPORTANT_FILES:
                important_files.append(
                    str(file_path.relative_to(root)).replace("\\", "/")
                )

    # Detect dependencies and frameworks
    dependencies = read_dependency_names(root)

    frameworks = set()
    backend_technologies = set()

    for dependency in dependencies:
        normalized = dependency.lower().replace("_", "-")

        for indicator, framework in FRAMEWORK_INDICATORS.items():
            if normalized == indicator:
                frameworks.add(framework)

        for indicator, technology in BACKEND_TECHNOLOGY_INDICATORS.items():
            if normalized == indicator:
                backend_technologies.add(technology)

        runtime = BACKEND_RUNTIME_INDICATORS.get(normalized)
        if runtime:
            backend_technologies.add(runtime)

    return {
        "project_name": root.name,
        "project_directory": str(root),
        "total_files_scanned": scanned_files,
        "skipped_files": skipped_files,
        "programming_languages": [
            {
                "language": language,
                "file_count": count
            }
            for language, count in languages.most_common()
        ],
        "detected_frameworks": sorted(frameworks),
        "backend_technologies": sorted(backend_technologies),
        "dependencies": sorted(dependencies),
        "important_files": sorted(important_files),
        "folder_structure": sorted(set(file_structure)),
    }
