from __future__ import annotations

from enum import StrEnum

from fastapi import HTTPException, status


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    ENGINEER = "engineer"
    ANALYST = "analyst"


ROLE_LEVEL = {
    Role.OWNER: 100,
    Role.ADMIN: 80,
    Role.ENGINEER: 60,
    Role.ANALYST: 20,
}


def ensure_role(user_role: str, minimum_role: Role) -> None:
    try:
        current_level = ROLE_LEVEL[Role(user_role)]
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown role.") from exc

    if current_level < ROLE_LEVEL[minimum_role]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role.")
