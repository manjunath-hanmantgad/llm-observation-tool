from __future__ import annotations

import argparse
import fnmatch
import re
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXCLUDE_PATTERNS = (
    ".git",
    ".git/*",
    ".env",
    ".venv",
    ".venv/*",
    ".pytest_cache",
    ".pytest_cache/*",
    ".ruff_cache",
    ".ruff_cache/*",
    ".DS_Store",
    "__pycache__",
    "*/__pycache__",
    "*/__pycache__/*",
    "*.pyc",
    "*.pyo",
    "*.egg-info",
    "*.egg-info/*",
    "storage/*.db",
    "storage/*.db-*",
    "storage/*.db.tmp",
    "storage/*.db.wal",
    "storage/*.duckdb",
    "storage/*.sqlite",
    "docs/issues.md",
    "docs/phase-1-enterprise-gaps.md",
    "docs/public-release.md",
    "scripts/prepare_public_release.py",
)

REQUIRED_FILES = (
    "README.md",
    ".env.example",
    ".github/workflows/ci.yml",
    "Dockerfile",
    "docker-compose.yml",
    "alembic.ini",
    "requirements.txt",
    "pyproject.toml",
    "demo/llm-observatory-dashboard.png",
    "demo/llm-observatory-incidents.png",
    "demo/llm-observatory-api-keys.png",
    "docs/api.md",
    "docs/auth.md",
    "docs/dashboard.md",
    "docs/deployment.md",
    "docs/operations.md",
    "docs/roadmap.md",
)

FORBIDDEN_PATTERNS = (
    ".env",
    ".venv/*",
    "*.db",
    "*.sqlite",
    "*.duckdb",
    "*.pyc",
    "__pycache__/*",
    ".pytest_cache/*",
    "docs/issues.md",
    "docs/phase-1-enterprise-gaps.md",
    "docs/public-release.md",
    "scripts/prepare_public_release.py",
)

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
)


def matches(path: Path, patterns: tuple[str, ...]) -> bool:
    rel = path.as_posix()
    return any(fnmatch.fnmatch(rel, pattern) for pattern in patterns)


def should_copy(path: Path) -> bool:
    relative = path.relative_to(PROJECT_ROOT)
    return not matches(relative, EXCLUDE_PATTERNS)


def copy_project(destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    for source in PROJECT_ROOT.rglob("*"):
        if source == destination or destination in source.parents:
            continue
        if not should_copy(source):
            continue
        target = destination / source.relative_to(PROJECT_ROOT)
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def validate_required_files(destination: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if not (destination / relative).exists():
            errors.append(f"missing required file: {relative}")
    return errors


def validate_forbidden_files(destination: Path) -> list[str]:
    errors: list[str] = []
    for path in destination.rglob("*"):
        if path.is_dir():
            continue
        relative = path.relative_to(destination)
        if matches(relative, FORBIDDEN_PATTERNS):
            errors.append(f"forbidden file included: {relative.as_posix()}")
    return errors


def validate_secrets(destination: Path) -> list[str]:
    errors: list[str] = []
    for path in destination.rglob("*"):
        if path.is_dir() or path.suffix.lower() in {".png", ".gif", ".jpg", ".jpeg", ".ico"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible secret pattern in {path.relative_to(destination).as_posix()}")
                break
    return errors


def validate(destination: Path) -> list[str]:
    return [
        *validate_required_files(destination),
        *validate_forbidden_files(destination),
        *validate_secrets(destination),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a clean standalone public release artifact.")
    parser.add_argument(
        "--destination",
        default="/private/tmp/llm-observatory-public",
        help="Directory to recreate with public-release files.",
    )
    args = parser.parse_args()

    destination = Path(args.destination).resolve()
    copy_project(destination)
    errors = validate(destination)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    file_count = sum(1 for path in destination.rglob("*") if path.is_file())
    print(f"Public release artifact ready: {destination}")
    print(f"Files included: {file_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
