
import ast
import os
from pathlib import Path


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    ".next",
    "vendor"
}

IGNORED_FILES = {
    ".env",
    ".env.local",
    ".env.production"
}

MAX_SOURCE_FILES = 3000
MAX_FILE_SIZE = 1024 * 1024  # 1 MB per Python file


def get_decorator_name(node):
    """Convert a decorator into readable text."""

    try:
        return ast.unparse(node)
    except Exception:
        return "unknown"


def get_function_details(node, file_path, class_name=None):
    """Extract information about a function or method."""

    decorators = [
        get_decorator_name(decorator)
        for decorator in node.decorator_list
    ]

    parameters = []

    for argument in node.args.args:
        parameters.append(argument.arg)

    return {
        "name": node.name,
        "file": file_path,
        "line": node.lineno,
        "end_line": getattr(node, "end_lineno", None),
        "class": class_name,
        "parameters": parameters,
        "decorators": decorators,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "docstring": ast.get_docstring(node)
    }


def analyze_python_file(file_path, project_root):
    """Analyze one Python file using Python AST."""

    relative_path = str(
        file_path.relative_to(project_root)
    ).replace("\\", "/")

    try:
        source = file_path.read_text(
            encoding="utf-8",
            errors="replace"
        )

        tree = ast.parse(source, filename=relative_path)

    except (OSError, SyntaxError, ValueError) as error:
        return {
            "file": relative_path,
            "error": str(error)
        }

    imports = []
    classes = []
    functions = []
    api_routes = []

    for node in ast.walk(tree):

        # Detect normal imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "module": alias.name,
                    "line": node.lineno
                })

        # Detect from-import statements
        elif isinstance(node, ast.ImportFrom):
            imports.append({
                "module": node.module or "",
                "line": node.lineno
            })

        # Detect class definitions
        elif isinstance(node, ast.ClassDef):
            bases = [
                ast.unparse(base)
                for base in node.bases
            ]

            classes.append({
                "name": node.name,
                "file": relative_path,
                "line": node.lineno,
                "bases": bases,
                "docstring": ast.get_docstring(node)
            })

            # Detect methods inside classes
            for child in node.body:
                if isinstance(
                    child,
                    (ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    functions.append(
                        get_function_details(
                            child,
                            relative_path,
                            class_name=node.name
                        )
                    )

        # Detect standalone functions
        elif isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            parent_class = None

            # Avoid duplicating methods already collected above
            for class_node in ast.walk(tree):
                if isinstance(class_node, ast.ClassDef):
                    if node in class_node.body:
                        parent_class = class_node.name
                        break

            if parent_class is None:
                functions.append(
                    get_function_details(
                        node,
                        relative_path
                    )
                )

        # Detect common FastAPI and Flask route decorators
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            for decorator in node.decorator_list:

                if not isinstance(decorator, ast.Call):
                    continue

                function = decorator.func

                if not isinstance(function, ast.Attribute):
                    continue

                method = function.attr.upper()

                supported_methods = {
                    "GET",
                    "POST",
                    "PUT",
                    "PATCH",
                    "DELETE",
                    "OPTIONS",
                    "HEAD",
                    "API_ROUTE"
                }

                if method not in supported_methods:
                    continue

                path = None

                if decorator.args:
                    first_argument = decorator.args[0]

                    if isinstance(first_argument, ast.Constant):
                        if isinstance(first_argument.value, str):
                            path = first_argument.value

                if path:
                    http_method = (
                        "MULTIPLE"
                        if method == "API_ROUTE"
                        else method
                    )

                    api_routes.append({
                        "method": http_method,
                        "path": path,
                        "function": node.name,
                        "file": relative_path,
                        "line": node.lineno
                    })

    return {
        "file": relative_path,
        "imports": imports,
        "classes": classes,
        "functions": functions,
        "api_routes": api_routes,
        "docstring": ast.get_docstring(tree),
        "status": "analyzed"
    }


def analyze_python_project(project_directory):
    """Analyze all eligible Python files in a project."""

    root = Path(project_directory).resolve()

    if not root.exists() or not root.is_dir():
        raise ValueError("Project directory does not exist.")

    file_results = []
    scanned_count = 0
    skipped_count = 0

    for current_root, directories, filenames in os.walk(root):

        current_path = Path(current_root)

        directories[:] = [
            directory for directory in directories
            if directory not in IGNORED_DIRECTORIES
            and not (current_path / directory).is_symlink()
        ]

        for filename in filenames:

            if not filename.endswith(".py"):
                continue

            if filename.lower() in IGNORED_FILES:
                skipped_count += 1
                continue

            file_path = current_path / filename

            if file_path.is_symlink():
                skipped_count += 1
                continue

            if file_path.stat().st_size > MAX_FILE_SIZE:
                skipped_count += 1
                continue

            scanned_count += 1

            if scanned_count > MAX_SOURCE_FILES:
                raise ValueError(
                    "Project contains too many Python files."
                )

            result = analyze_python_file(file_path, root)
            file_results.append(result)

    all_imports = set()
    all_classes = []
    all_functions = []
    all_routes = []
    analysis_errors = []

    for result in file_results:

        if result.get("status") != "analyzed":
            analysis_errors.append(result)
            continue

        for item in result["imports"]:
            all_imports.add(item["module"])

        all_classes.extend(result["classes"])
        all_functions.extend(result["functions"])
        all_routes.extend(result["api_routes"])

    return {
        "analysis_type": "static_python_ast_analysis",
        "python_files_scanned": scanned_count,
        "skipped_files": skipped_count,
        "total_imports": len(all_imports),
        "imports": sorted(all_imports),
        "total_classes": len(all_classes),
        "classes": all_classes,
        "total_functions": len(all_functions),
        "functions": all_functions,
        "total_api_routes": len(all_routes),
        "api_routes": all_routes,
        "file_analysis": file_results,
        "analysis_errors": analysis_errors
    }
