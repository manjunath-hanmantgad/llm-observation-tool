from __future__ import annotations

import json

from sqlalchemy.orm import Session

from observatory.models import AuditLog


def write_audit_log(
    session: Session,
    *,
    organization_id: str,
    action: str,
    actor_user_id: str | None = None,
    target_type: str = "",
    target_id: str = "",
    metadata: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=json.dumps(metadata or {}),
        )
    )
