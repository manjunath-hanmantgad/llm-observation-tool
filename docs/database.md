# Database

The application now has two persistence paths:

1. Existing DuckDB local metrics store used by the original mock gateway and Streamlit dashboard.
2. SQLAlchemy application database for enterprise entities and ingestion APIs.

## Application Database

Configured with:

```env
DATABASE_URL=sqlite:///storage/observatory.db
```

For production:

```env
DATABASE_URL=postgresql+psycopg://observatory:change_me@postgres:5432/observatory
```

## Migrations

Alembic is configured under:

- `alembic.ini`
- `migrations/env.py`
- `migrations/versions/0001_enterprise_foundation.py`

Run migrations:

```bash
alembic upgrade head
```

## Core Tables

- organizations
- users
- api_keys
- projects
- endpoints
- llm_provider_models
- llm_calls
- token_cost_records
- evaluation_jobs
- platform_evaluation_results
- alert_rules
- incidents
- audit_logs
