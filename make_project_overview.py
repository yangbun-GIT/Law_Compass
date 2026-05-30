from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


EXCLUDE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".turbo",
    ".cache",
    "coverage",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".output",
    "target",
    "out",
    "logs",
    "tmp",
    "temp",
    "submission_outputs",

    # Law Compass 같은 프로젝트에서 커질 수 있는 실행/업로드 산출물
    "storage",
    "uploads",
    "processed",
    "reports",
    "db-backups",
    "quarantine",
}

TARGET_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".vue",
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".json",
    ".md",
    ".txt",
    ".example",
    ".sample",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".sql",
    ".sh",
    ".bash",
    ".bat",
    ".ps1",
    ".dockerignore",
    ".gitignore",
}

INCLUDE_FILE_NAMES = {
    "Dockerfile",
    "dockerfile",
    "Containerfile",
    "Makefile",
    "Caddyfile",
    "Procfile",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "Pipfile",
    "package.json",
    "vite.config.ts",
    "vite.config.js",
    "tsconfig.json",
    "README.md",
}

EXCLUDE_FILES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
    "project_combined.txt",
    "project_overview.md",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
}

PRIORITY_FILE_PATTERNS = [
    "README",
    "docker-compose",
    "compose",
    "Dockerfile",
    "Caddyfile",
    "package.json",
    "requirements",
    "pyproject.toml",
    "main.py",
    "app.py",
    "server.",
    "index.",
    "routes",
    "router",
    "api",
    "gateway",
    "agent",
    "worker",
    "schema",
    "models",
    "migration",
    "migrations",
    "vite.config",
    "tsconfig",
]


@dataclass(frozen=True)
class FileInfo:
    path: Path
    rel: str
    size: int


def should_skip_dir(directory_name: str) -> bool:
    # GitHub Actions 흐름 파악용
    if directory_name == ".github":
        return False
    return directory_name in EXCLUDE_DIRS or directory_name.startswith(".")


def should_include_file(path: Path) -> bool:
    name = path.name

    if name in EXCLUDE_FILES:
        return False

    # 실제 비밀값이 들어갈 수 있는 env는 제외하고 예시 파일만 포함
    if name.startswith(".env") and name not in {".env.example", ".env.sample"}:
        return False

    if name in INCLUDE_FILE_NAMES:
        return True

    return path.suffix.lower() in TARGET_EXTENSIONS


def is_binary_file(path: Path, sample_size: int = 2048) -> bool:
    try:
        chunk = path.read_bytes()[:sample_size]
    except Exception:
        return True
    return b"\x00" in chunk


def sort_key(info: FileInfo) -> tuple[int, str]:
    rel_lower = info.rel.lower()
    priority = 99

    for index, pattern in enumerate(PRIORITY_FILE_PATTERNS):
        if pattern.lower() in rel_lower:
            priority = min(priority, index)

    return priority, rel_lower


def collect_files(root_path: Path, max_file_size: int) -> list[FileInfo]:
    files: list[FileInfo] = []

    for root, dirs, file_names in os.walk(root_path):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]

        for file_name in file_names:
            path = Path(root) / file_name

            if not should_include_file(path):
                continue

            try:
                resolved = path.resolve()
                size = resolved.stat().st_size
            except OSError:
                continue

            if size > max_file_size:
                continue

            if is_binary_file(path):
                continue

            rel = str(path.relative_to(root_path)).replace("\\", "/")
            files.append(FileInfo(path=path, rel=rel, size=size))

    return sorted(files, key=sort_key)


def read_text(path: Path, max_chars: int | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        return f"[Error reading file: {exc}]"

    if max_chars is not None and len(text) > max_chars:
        omitted = len(text) - max_chars
        return text[:max_chars] + f"\n\n... [TRUNCATED: {omitted:,} chars omitted] ...\n"

    return text


def code_fence_lang(path: Path) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower()

    if name in {"dockerfile", "containerfile"}:
        return "dockerfile"
    if name == "caddyfile":
        return "caddyfile"
    if name.startswith(".env") or suffix in {".example", ".sample"}:
        return "dotenv"

    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "jsx",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".vue": "vue",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".json": "json",
        ".md": "markdown",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".sql": "sql",
        ".sh": "bash",
        ".bash": "bash",
        ".bat": "bat",
        ".ps1": "powershell",
        ".txt": "text",
    }
    return mapping.get(suffix, "text")


def safe_for_markdown_fence(text: str) -> str:
    return text.replace("```", "``\u200b`")


def write_directory_tree(outfile, root_path: Path, max_depth: int) -> None:
    outfile.write("## 1. 프로젝트 디렉터리 구조\n\n")
    outfile.write("```text\n")
    outfile.write(f"{root_path.name}/\n")

    for root, dirs, file_names in os.walk(root_path):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]
        current = Path(root)
        depth = len(current.relative_to(root_path).parts)

        if depth >= max_depth:
            dirs[:] = []
            continue

        indent = "    " * depth

        for directory in sorted(dirs):
            outfile.write(f"{indent}    - {directory}/\n")

        included_files = [
            f for f in sorted(file_names)
            if should_include_file(current / f)
        ]

        for file_name in included_files:
            outfile.write(f"{indent}    - {file_name}\n")

    outfile.write("```\n\n")


def extract_package_info(files: list[FileInfo]) -> list[dict]:
    result: list[dict] = []

    for info in files:
        if info.path.name != "package.json":
            continue

        text = read_text(info.path)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            result.append({"file": info.rel, "error": "Invalid package.json"})
            continue

        result.append({
            "file": info.rel,
            "name": data.get("name"),
            "version": data.get("version"),
            "scripts": data.get("scripts", {}),
            "dependencies": sorted((data.get("dependencies") or {}).keys()),
            "devDependencies": sorted((data.get("devDependencies") or {}).keys()),
        })

    return result


def extract_requirements(files: list[FileInfo]) -> list[dict]:
    result: list[dict] = []

    for info in files:
        lower = info.path.name.lower()
        if not (lower.startswith("requirements") and lower.endswith(".txt")):
            continue

        lines = []
        for raw_line in read_text(info.path).splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            lines.append(line)

        result.append({
            "file": info.rel,
            "packages": lines,
        })

    return result


def extract_env_keys(files: list[FileInfo]) -> dict[str, list[str]]:
    env_files: dict[str, list[str]] = {}

    env_file_names = {
        ".env.example",
        ".env.sample",
        "env.example",
        "env.sample",
    }

    for info in files:
        if info.path.name not in env_file_names and not info.path.name.endswith(".env.example"):
            continue

        keys: list[str] = []
        for line in read_text(info.path).splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key = stripped.split("=", 1)[0].strip()
            if key:
                keys.append(key)

        env_files[info.rel] = sorted(set(keys))

    return env_files


def extract_env_usages(files: list[FileInfo]) -> dict[str, list[str]]:
    patterns = [
        re.compile(r"os\.getenv\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']"),
        re.compile(r"os\.environ\.get\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']"),
        re.compile(r"os\.environ\[\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']\s*\]"),
        re.compile(r"process\.env\.([A-Za-z_][A-Za-z0-9_]*)"),
        re.compile(r"import\.meta\.env\.([A-Za-z_][A-Za-z0-9_]*)"),
    ]

    usages: dict[str, list[str]] = {}

    for info in files:
        if info.path.suffix.lower() not in {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue"}:
            continue

        text = read_text(info.path)
        found: set[str] = set()

        for pattern in patterns:
            found.update(pattern.findall(text))

        if found:
            usages[info.rel] = sorted(found)

    return usages


def extract_python_routes(files: list[FileInfo]) -> list[dict]:
    route_pattern = re.compile(
        r"^\s*@(?P<object>[A-Za-z_][A-Za-z0-9_\.]*)\."
        r"(?P<method>get|post|put|patch|delete|options|head)"
        r"\(\s*[\"'](?P<path>[^\"']+)[\"']",
        re.MULTILINE,
    )
    prefix_pattern = re.compile(
        r"(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*APIRouter\("
        r"(?P<body>.*?)\)",
        re.DOTALL,
    )
    prefix_value_pattern = re.compile(r"prefix\s*=\s*[\"']([^\"']+)[\"']")

    routes: list[dict] = []

    for info in files:
        if info.path.suffix.lower() != ".py":
            continue

        text = read_text(info.path)

        prefixes: dict[str, str] = {}
        for prefix_match in prefix_pattern.finditer(text):
            var = prefix_match.group("var")
            body = prefix_match.group("body")
            prefix_value = prefix_value_pattern.search(body)
            if prefix_value:
                prefixes[var] = prefix_value.group(1)

        for match in route_pattern.finditer(text):
            obj = match.group("object").split(".")[-1]
            method = match.group("method").upper()
            path = match.group("path")
            prefix = prefixes.get(obj, "")

            routes.append({
                "file": info.rel,
                "method": method,
                "path": prefix + path if prefix and not path.startswith(prefix) else path,
                "decorator_object": match.group("object"),
            })

    return routes


def extract_js_routes(files: list[FileInfo]) -> list[dict]:
    route_pattern = re.compile(
        r"(?P<object>\b(?:app|router|server|fastify|expressRouter)\b)"
        r"\.(?P<method>get|post|put|patch|delete|options|head|use)"
        r"\(\s*[\"'`](?P<path>[^\"'`]+)[\"'`]",
        re.MULTILINE,
    )

    routes: list[dict] = []

    for info in files:
        if info.path.suffix.lower() not in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}:
            continue

        text = read_text(info.path)
        for match in route_pattern.finditer(text):
            routes.append({
                "file": info.rel,
                "method": match.group("method").upper(),
                "path": match.group("path"),
                "object": match.group("object"),
            })

    return routes


def extract_frontend_routes(files: list[FileInfo]) -> list[dict]:
    path_pattern = re.compile(r"\bpath\s*:\s*[\"'`]([^\"'`]+)[\"'`]")
    routes: list[dict] = []

    for info in files:
        if info.path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx", ".vue"}:
            continue

        rel_lower = info.rel.lower()
        if "router" not in rel_lower and "routes" not in rel_lower:
            continue

        text = read_text(info.path)
        for match in path_pattern.finditer(text):
            routes.append({
                "file": info.rel,
                "path": match.group(1),
            })

    return routes


def extract_http_calls(files: list[FileInfo]) -> list[dict]:
    patterns = [
        re.compile(r"\bfetch\(\s*[\"'`]([^\"'`]+)[\"'`]"),
        re.compile(r"\baxios\.(?:get|post|put|patch|delete)\(\s*[\"'`]([^\"'`]+)[\"'`]"),
        re.compile(r"\bapi\.(?:get|post|put|patch|delete)\(\s*[\"'`]([^\"'`]+)[\"'`]"),
        re.compile(r"\bhttp\.(?:get|post|put|patch|delete)\(\s*[\"'`]([^\"'`]+)[\"'`]"),
    ]

    calls: list[dict] = []

    for info in files:
        if info.path.suffix.lower() not in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue"}:
            continue

        text = read_text(info.path)
        found: set[str] = set()

        for pattern in patterns:
            found.update(pattern.findall(text))

        for url in sorted(found):
            calls.append({
                "file": info.rel,
                "url": url,
            })

    return calls


def extract_compose_services(files: list[FileInfo]) -> list[dict]:
    compose_files = [
        info for info in files
        if "compose" in info.path.name.lower() and info.path.suffix.lower() in {".yml", ".yaml"}
    ]

    services: list[dict] = []

    for info in compose_files:
        lines = read_text(info.path).splitlines()
        in_services = False
        services_indent = 0
        current_service: dict | None = None
        current_indent = 0

        for line in lines:
            if not line.strip() or line.lstrip().startswith("#"):
                continue

            indent = len(line) - len(line.lstrip(" "))
            stripped = line.strip()

            if stripped == "services:":
                in_services = True
                services_indent = indent
                continue

            if not in_services:
                continue

            if indent <= services_indent and not stripped.startswith("-"):
                current_service = None
                break

            service_match = re.match(r"^([A-Za-z0-9_-]+):\s*$", stripped)
            if service_match and indent == services_indent + 2:
                current_service = {
                    "compose_file": info.rel,
                    "name": service_match.group(1),
                    "build": None,
                    "image": None,
                    "ports": [],
                    "depends_on": [],
                }
                current_indent = indent
                services.append(current_service)
                continue

            if current_service is None:
                continue

            if indent <= current_indent:
                current_service = None
                continue

            if stripped.startswith("build:"):
                current_service["build"] = stripped.split(":", 1)[1].strip() or "(object)"
            elif stripped.startswith("image:"):
                current_service["image"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- ") and ("\"" in stripped or ":" in stripped):
                value = stripped[2:].strip().strip("\"'")
                if re.search(r"\d+:\d+", value):
                    current_service["ports"].append(value)
            elif stripped.startswith("depends_on:"):
                current_service["depends_on"].append("(see compose file)")

    return services


def classify_important_files(files: list[FileInfo]) -> dict[str, list[str]]:
    categories = {
        "컨테이너/배포": [],
        "백엔드/API": [],
        "프론트엔드": [],
        "워커/비동기 작업": [],
        "DB/스키마/마이그레이션": [],
        "설정/환경": [],
        "문서": [],
        "테스트": [],
    }

    for info in files:
        rel = info.rel.lower()
        name = info.path.name.lower()

        if "docker" in name or "compose" in name or name in {"caddyfile", "makefile"}:
            categories["컨테이너/배포"].append(info.rel)
        elif any(token in rel for token in ["/api/", "/routes/", "/routers/", "gateway", "server.", "main.py", "app.py"]):
            categories["백엔드/API"].append(info.rel)
        elif any(token in rel for token in ["frontend", "src/", ".vue", "vite.config", "components", "pages", "views"]):
            categories["프론트엔드"].append(info.rel)
        elif "worker" in rel or "queue" in rel or "celery" in rel or "rq" in rel:
            categories["워커/비동기 작업"].append(info.rel)
        elif any(token in rel for token in ["migration", "migrations", "schema", "models", "database", ".sql"]):
            categories["DB/스키마/마이그레이션"].append(info.rel)
        elif any(token in name for token in ["requirements", "package.json", "pyproject", "tsconfig"]) or ".env.example" in name:
            categories["설정/환경"].append(info.rel)
        elif name.endswith(".md") or "readme" in name:
            categories["문서"].append(info.rel)
        elif "test" in rel or "spec" in rel:
            categories["테스트"].append(info.rel)

    return {key: sorted(set(value)) for key, value in categories.items() if value}


def write_list_section(outfile, title: str, items: Iterable[str], empty_text: str = "감지된 항목 없음") -> None:
    outfile.write(f"### {title}\n\n")
    item_list = list(items)

    if not item_list:
        outfile.write(f"- {empty_text}\n\n")
        return

    for item in item_list:
        outfile.write(f"- `{item}`\n")
    outfile.write("\n")


def write_analysis_sections(outfile, files: list[FileInfo]) -> None:
    outfile.write("## 2. 자동 감지 요약\n\n")

    categories = classify_important_files(files)
    for category, items in categories.items():
        write_list_section(outfile, category, items[:80])

    compose_services = extract_compose_services(files)
    outfile.write("## 3. Docker Compose 서비스 추정\n\n")
    if compose_services:
        outfile.write("| compose 파일 | 서비스 | build | image | ports |\n")
        outfile.write("|---|---|---|---|---|\n")
        for service in compose_services:
            ports = ", ".join(service.get("ports") or [])
            outfile.write(
                f"| `{service['compose_file']}` "
                f"| `{service['name']}` "
                f"| `{service.get('build') or ''}` "
                f"| `{service.get('image') or ''}` "
                f"| `{ports}` |\n"
            )
        outfile.write("\n")
    else:
        outfile.write("감지된 docker-compose 서비스가 없습니다.\n\n")

    packages = extract_package_info(files)
    outfile.write("## 4. Node/Frontend package.json 요약\n\n")
    if packages:
        for package in packages:
            outfile.write(f"### `{package['file']}`\n\n")
            outfile.write(f"- name: `{package.get('name')}`\n")
            outfile.write(f"- version: `{package.get('version')}`\n")
            outfile.write("- scripts:\n")
            for key, value in (package.get("scripts") or {}).items():
                outfile.write(f"  - `{key}`: `{value}`\n")
            outfile.write("- dependencies:\n")
            deps = package.get("dependencies") or []
            outfile.write("  - " + (", ".join(f"`{dep}`" for dep in deps[:80]) if deps else "없음") + "\n")
            outfile.write("- devDependencies:\n")
            dev_deps = package.get("devDependencies") or []
            outfile.write("  - " + (", ".join(f"`{dep}`" for dep in dev_deps[:80]) if dev_deps else "없음") + "\n\n")
    else:
        outfile.write("감지된 package.json이 없습니다.\n\n")

    requirements = extract_requirements(files)
    outfile.write("## 5. Python requirements 요약\n\n")
    if requirements:
        for req in requirements:
            outfile.write(f"### `{req['file']}`\n\n")
            for package in req["packages"][:120]:
                outfile.write(f"- `{package}`\n")
            if len(req["packages"]) > 120:
                outfile.write(f"- ... {len(req['packages']) - 120}개 생략\n")
            outfile.write("\n")
    else:
        outfile.write("감지된 requirements.txt가 없습니다.\n\n")

    env_keys = extract_env_keys(files)
    env_usages = extract_env_usages(files)
    outfile.write("## 6. 환경변수 흐름\n\n")
    outfile.write("### .env.example / .env.sample에 정의된 키\n\n")
    if env_keys:
        for file, keys in env_keys.items():
            outfile.write(f"- `{file}`: " + ", ".join(f"`{key}`" for key in keys) + "\n")
        outfile.write("\n")
    else:
        outfile.write("- 감지된 예시 env 파일이 없습니다.\n\n")

    outfile.write("### 코드에서 사용되는 환경변수\n\n")
    if env_usages:
        for file, keys in sorted(env_usages.items()):
            outfile.write(f"- `{file}`: " + ", ".join(f"`{key}`" for key in keys) + "\n")
        outfile.write("\n")
    else:
        outfile.write("- 코드에서 직접 감지된 환경변수가 없습니다.\n\n")

    python_routes = extract_python_routes(files)
    js_routes = extract_js_routes(files)
    frontend_routes = extract_frontend_routes(files)
    http_calls = extract_http_calls(files)

    outfile.write("## 7. API / 라우트 흐름 추정\n\n")

    outfile.write("### Python FastAPI/Flask 계열 라우트\n\n")
    if python_routes:
        outfile.write("| Method | Path | File |\n")
        outfile.write("|---|---|---|\n")
        for route in python_routes:
            outfile.write(f"| `{route['method']}` | `{route['path']}` | `{route['file']}` |\n")
        outfile.write("\n")
    else:
        outfile.write("- 감지된 Python 라우트가 없습니다.\n\n")

    outfile.write("### JS/TS Express 계열 라우트\n\n")
    if js_routes:
        outfile.write("| Method | Path | File |\n")
        outfile.write("|---|---|---|\n")
        for route in js_routes:
            outfile.write(f"| `{route['method']}` | `{route['path']}` | `{route['file']}` |\n")
        outfile.write("\n")
    else:
        outfile.write("- 감지된 JS/TS 라우트가 없습니다.\n\n")

    outfile.write("### Frontend Router path\n\n")
    if frontend_routes:
        outfile.write("| Path | File |\n")
        outfile.write("|---|---|\n")
        for route in frontend_routes:
            outfile.write(f"| `{route['path']}` | `{route['file']}` |\n")
        outfile.write("\n")
    else:
        outfile.write("- 감지된 프론트엔드 라우터 path가 없습니다.\n\n")

    outfile.write("### 프론트엔드/클라이언트에서 호출하는 API URL 후보\n\n")
    if http_calls:
        outfile.write("| URL | File |\n")
        outfile.write("|---|---|\n")
        for call in http_calls[:300]:
            outfile.write(f"| `{call['url']}` | `{call['file']}` |\n")
        if len(http_calls) > 300:
            outfile.write(f"\n> {len(http_calls) - 300}개 URL 후보 생략\n")
        outfile.write("\n")
    else:
        outfile.write("- 감지된 fetch/axios/api 호출이 없습니다.\n\n")


def write_file_contents(
    outfile,
    files: list[FileInfo],
    max_file_chars: int,
    max_total_chars: int,
) -> None:
    outfile.write("## 8. 주요 파일 내용\n\n")
    outfile.write(
        "아래 내용은 프로젝트 흐름 파악용으로 자동 병합된 파일입니다. "
        "민감한 `.env` 파일과 대용량 실행 산출물은 제외됩니다.\n\n"
    )

    total_chars = 0

    for info in files:
        if total_chars >= max_total_chars:
            outfile.write(f"\n> 전체 출력 제한 `{max_total_chars:,}`자를 초과하여 이후 파일은 생략했습니다.\n")
            break

        remaining = max_total_chars - total_chars
        limit = min(max_file_chars, remaining)
        text = read_text(info.path, max_chars=limit)
        text = safe_for_markdown_fence(text)

        outfile.write(f"### File: `{info.rel}`\n\n")
        outfile.write(f"- size: `{info.size:,}` bytes\n\n")
        outfile.write(f"```{code_fence_lang(info.path)}\n")
        outfile.write(text)
        outfile.write("\n```\n\n")

        total_chars += len(text)


def generate_project_overview(
    root_dir: str,
    output_file: str,
    max_depth: int,
    max_file_size: int,
    max_file_chars: int,
    max_total_chars: int,
) -> None:
    root_path = Path(root_dir).resolve()
    output_path = Path(output_file).resolve()

    if not root_path.exists():
        raise FileNotFoundError(f"root_dir not found: {root_path}")

    files = collect_files(root_path, max_file_size=max_file_size)
    files = [info for info in files if info.path.resolve() != output_path]

    with output_path.open("w", encoding="utf-8") as outfile:
        outfile.write("# PROJECT OVERVIEW FOR CODE ANALYSIS\n\n")
        outfile.write(
            "이 문서는 프로젝트의 전체 구조, 실행 흐름, 서비스 구성, API 라우트, "
            "환경변수, 주요 파일 내용을 파악하기 위해 자동 생성되었습니다.\n\n"
        )

        outfile.write("## 0. 생성 정보\n\n")
        outfile.write(f"- Root: `{root_path}`\n")
        outfile.write(f"- Generated at: `{datetime.now().isoformat(timespec='seconds')}`\n")
        outfile.write(f"- Included files: `{len(files)}`\n")
        outfile.write(f"- Max file size: `{max_file_size:,}` bytes\n")
        outfile.write(f"- Max chars per file: `{max_file_chars:,}` chars\n")
        outfile.write(f"- Max total chars: `{max_total_chars:,}` chars\n\n")

        write_directory_tree(outfile, root_path, max_depth=max_depth)
        write_analysis_sections(outfile, files)
        write_file_contents(
            outfile,
            files,
            max_file_chars=max_file_chars,
            max_total_chars=max_total_chars,
        )

    print(f"프로젝트 분석용 문서 생성 완료: {output_path}")
    print(f"포함 파일 수: {len(files)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="프로젝트 구조와 흐름 파악용 Markdown 문서를 생성합니다."
    )
    parser.add_argument(
        "--root",
        default="./",
        help="분석할 프로젝트 루트 경로. 기본값: ./",
    )
    parser.add_argument(
        "--out",
        default="project_overview.md",
        help="출력 파일명. 기본값: project_overview.md",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
        help="디렉터리 트리 출력 깊이. 기본값: 5",
    )
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=1_000_000,
        help="포함할 개별 파일 최대 크기 bytes. 기본값: 1,000,000",
    )
    parser.add_argument(
        "--max-file-chars",
        type=int,
        default=80_000,
        help="파일 하나당 출력할 최대 문자 수. 기본값: 80,000",
    )
    parser.add_argument(
        "--max-total-chars",
        type=int,
        default=3_000_000,
        help="전체 파일 내용 출력 최대 문자 수. 기본값: 3,000,000",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate_project_overview(
        root_dir=args.root,
        output_file=args.out,
        max_depth=args.max_depth,
        max_file_size=args.max_file_size,
        max_file_chars=args.max_file_chars,
        max_total_chars=args.max_total_chars,
    )