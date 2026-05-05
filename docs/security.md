# Security

## Secret Handling

- `.env` is ignored by Git.
- `.env.example` contains safe placeholders only.
- Raw API keys are returned only at creation.
- API key hashes are stored with HMAC-SHA256 and an environment-provided pepper.
- Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes.

## Tenant Isolation

Authenticated routes derive organization scope from the JWT. Service ingestion derives organization scope from the API key. If an API key is scoped to a project, ingestion into any other project is rejected.

## CORS

CORS origins are configured through:

```env
CORS_ALLOWED_ORIGINS=http://localhost:8501,http://localhost:8510
```

The API no longer uses a wildcard CORS default.

## Security Headers

The API sets:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Prompt and Response Storage

Ingestion supports `full`, `redacted`, and `metadata-only` storage modes. The current redaction hook is intentionally conservative and should be extended with a dedicated PII detector in a later phase.
