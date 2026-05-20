# Public Release Guide

This project can be published as a standalone public repository after production-readiness checks pass. Keep the broader portfolio workspace private and publish only the `01-llm-observatory` project folder.

## Recommended Public Repository

Suggested name:

```text
llm-observatory
```

Create the public repository empty, without a generated README, `.gitignore`, or license file. The project already contains its own README, `.gitignore`, CI workflow, Dockerfile, and documentation.

## Pre-Release Checklist

Run from `01-llm-observatory`:

```bash
pytest
alembic upgrade head
python demo/reset_demo.py
python demo/seed_platform_demo.py
python workers/evaluation_worker.py --limit 10
python workers/alert_worker.py
```

Docker is optional for public release. When Docker is available, run:

```bash
docker compose up --build
```

Confirm:

- `README.md` renders correctly on GitHub.
- Mermaid diagrams render in GitHub Markdown.
- `demo/llm-observatory-dashboard.png` is present.
- `demo/llm-observatory-incidents.png` is present.
- `demo/llm-observatory-api-keys.png` is present.
- `/health/ready` returns `{"status": "ready", "database": "ok"}`.
- `/metrics` returns Prometheus-compatible metrics.
- `.env.example` contains placeholders only.
- `.env`, `.venv`, `storage/*.db`, `__pycache__/`, and generated caches are not included.
- Docker Compose is documented as an optional path if it has not been verified locally.
- GitHub Actions passes after push.

## Files To Include

Include the project files under `01-llm-observatory`, including:

- `.env.example`
- `.github/workflows/ci.yml`
- `.gitignore`
- `README.md`
- `Dockerfile`
- `docker-compose.yml`
- `alembic.ini`
- `requirements.txt`
- `pyproject.toml`
- `alerts/`
- `dashboard/`
- `demo/`
- `docs/`
- `eval_engine/`
- `gateway/`
- `migrations/`
- `observatory/`
- `shared/`
- `storage/__init__.py`
- `storage/db.py`
- `tests/`
- `workers/`

## Files To Exclude

Do not include private workspace files such as:

- `../project_build_reference.md`
- `../social_media_playbook.md`
- `../user_project_requirements.md`
- `../issues_tracker.md`
- `../graphify-out/`
- `../list`
- other unfinished project folders

Also exclude local runtime artifacts:

- `.env`
- `.venv/`
- `storage/*.db`
- `.pytest_cache/`
- `__pycache__/`
- `docs/issues.md`
- `docs/phase-1-enterprise-gaps.md`
- `docs/public-release.md`
- `scripts/prepare_public_release.py`

## Build Public Artifact

Run from `01-llm-observatory`:

```bash
python scripts/prepare_public_release.py --destination /private/tmp/llm-observatory-public
```

The script recreates the destination directory, copies only public-release files, excludes local runtime artifacts, and validates required files. It also scans text files for common secret patterns.

## Publish Flow

Create an empty public repository, then push the prepared artifact:

```bash
cd /private/tmp/llm-observatory-public
git init -b main
git remote add origin https://github.com/<username>/llm-observatory.git
git add .
git commit -m "Release LLM Observatory"
git push -u origin main
```

After publishing, verify the repository page, CI status, README screenshot, and all internal links.
