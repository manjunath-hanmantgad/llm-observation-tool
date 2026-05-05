# Authentication and Authorization

The backend supports organization-scoped JWT authentication and service API keys.

## User Authentication

Registration creates an organization and its first owner user. Passwords are hashed with PBKDF2-HMAC-SHA256 and a per-password random salt. Raw passwords are never persisted.

JWT access tokens include user id, organization id, role, issuer, and expiry.

## Roles

Supported roles:

- `owner`
- `admin`
- `engineer`
- `analyst`

Current role rules:

- owner/admin can create and revoke API keys
- owner/admin/engineer can create projects and endpoints
- all authenticated users can list tenant projects and query tenant metrics

## API Keys

Service-to-service ingestion uses `X-API-Key`.

API key handling:

- generated key is shown once at creation
- persisted value is HMAC-SHA256 hash
- key prefix is stored for display and audit
- keys can be scoped to a project
- revoked keys are rejected

## Audit Logs

Audit logs are written for registration, login, project creation, endpoint creation, API key creation, and API key revocation.
