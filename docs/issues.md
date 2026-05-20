# LLM Observatory Issues Tracker

Use this file before debugging LLM Observatory. It records bugs and fixes already handled during implementation.

## Resolved Issues

### zsh Extras Requirement Globbing

- Symptom: `uv pip install SQLAlchemy==2.0.31 alembic==1.13.2 psycopg[binary]==3.2.1` failed with `zsh: no matches found`.
- Root cause: zsh treated `[binary]` as a glob pattern.
- Fix: Quote extras requirements, e.g. `'psycopg[binary]==3.2.1'`.
- Verification: dependencies installed successfully.

### FastAPI 204 Response Body Assertion

- Symptom: test collection failed with `AssertionError: Status code 204 must not have a response body`.
- Root cause: the API key revoke route used `204` while the function annotation allowed FastAPI to infer a response body.
- Fix: Return a `200` JSON status payload for revoke operations.
- Verification: `pytest` passed.

### Float Precision in Cost Test

- Symptom: `test_known_model_cost` failed because `0.0007499999999999999 != 0.00075`.
- Root cause: floating-point precision.
- Fix: Use `pytest.approx(0.00075)`.
- Verification: `pytest` passed.

### Pydantic Protected Namespace Warning

- Symptom: Pydantic warned that `model_purpose` conflicts with the protected `model_` namespace.
- Root cause: Pydantic v2 protects names beginning with `model_`.
- Fix: Added `ConfigDict(protected_namespaces=())` to `ChatRequest`.
- Verification: warning removed from project code path.

### Deprecated `datetime.utcnow`

- Symptom: Python 3.12 emitted deprecation warnings for `datetime.utcnow()`.
- Root cause: timezone-naive UTC timestamps.
- Fix: Replaced with `datetime.now(UTC)`.
- Verification: tests passed.

### Direct Script Import Failure

- Symptom: `python demo/seed_data.py` failed with `ModuleNotFoundError: No module named 'eval_engine'`.
- Root cause: running a nested script directly did not include the project root on `sys.path`.
- Fix: Added project root path insertion to direct-run scripts:
  - `demo/seed_data.py`
  - `eval_engine/run_evals.py`
  - `alerts/slack_alerts.py`
  - `dashboard/app.py`
- Verification: demo seed, evaluator, alerts, and dashboard run paths worked.

### DuckDB Lock During Concurrent Verification

- Symptom: demo seed failed with a DuckDB lock conflict while another process held `storage/metrics.db`.
- Root cause: tests/demo shared the same database file during concurrent commands.
- Fix: Added `LLM_OBSERVATORY_DB_PATH` support and isolated tests with `storage/test_metrics.db`.
- Verification: tests and demo seed both passed with separate DB paths.

### Streamlit Import Failure

- Symptom: dashboard started, then failed with `ModuleNotFoundError: No module named 'storage'`.
- Root cause: Streamlit execution path did not include project root.
- Fix: Added project root path insertion in `dashboard/app.py`.
- Verification: Streamlit restarted successfully.

### Dashboard Port Conflict

- Symptom: Streamlit could not use `8501`; user later reported `8502` was already used.
- Root cause: existing services occupied default ports.
- Fix: Restarted dashboard on `8510`.
- Verification: Streamlit reported URL `http://127.0.0.1:8510`.

## Open Issues

### Docker Verification Pending

- Symptom: Docker commands cannot be run.
- Root cause: Docker is not installed or not available in shell.
- Current status: Dockerfile and Docker Compose are implemented but not verified.
- Next step: Verify with `docker compose up --build` once Docker is available.

### Dashboard Uses Streamlit For Customer Demo Phase

- Context: The enterprise prompt preferred React/Next.js if appropriate.
- Decision: Current phase keeps Streamlit because the repo already had it, the backend is still evolving, and the immediate goal is a customer-demo-capable UX without adding a separate frontend toolchain.
- Follow-up: React/Next.js remains a later option if the project needs production UI packaging beyond a local/product demo.

### Evaluation And Alert Workers Are Synchronous Entry Points

- Context: A full production deployment would typically use Redis, Celery/RQ, Azure Service Bus, or a managed queue.
- Decision: Current phase implements deterministic synchronous worker commands and API-triggered execution first.
- Reason: This provides testable product behavior without adding queue infrastructure before Docker is available locally.
- Follow-up: Add queue backend once the Docker Compose environment is verified.

### Test Database Isolation

- Symptom: Shared SQLite/DuckDB test files can leak state across test runs and hide isolation bugs.
- Root cause: tests previously used fixed files under `storage/`.
- Fix: test configuration now creates a unique temporary directory and points `DATABASE_URL` plus `LLM_OBSERVATORY_DB_PATH` at per-run files.
- Verification: `pytest` passed.

### Alembic Conflict After Local `create_all`

- Symptom: running `alembic upgrade head` failed with `table organizations already exists` on a SQLite demo database.
- Root cause: local app/seeder startup can create tables through SQLAlchemy `create_all`; if Alembic is run later, the tables exist but `alembic_version` has not been stamped.
- Fix: `init_platform_db()` now stamps the initial Alembic revision when it creates/detects the initial schema without an Alembic version table.
- Verification: manual demo flow and tests were rerun after the fix.

### Do Not Parallelize Reset And Seed Against Same SQLite DB

- Symptom: `demo/seed_platform_demo.py` failed with `table organizations already exists`.
- Root cause: reset and seed commands were run in parallel against the same SQLite database file, creating a schema race.
- Fix: run demo reset and seed sequentially.
- Verification: sequential demo flow was rerun after recording this issue.

### Dashboard API Keys View Missing Projects Scope

- Symptom: clicking **API Keys** in the Streamlit dashboard raised `NameError: name 'projects' is not defined`.
- Root cause: the new API key create form expected a `projects` list, but the page dispatcher did not pass one from the current session scope.
- Fix: pass `org_projects(session, organization.id)` into `api_keys_view`.
- Verification: browser smoke test was rerun and the API Keys screenshot was captured successfully.
