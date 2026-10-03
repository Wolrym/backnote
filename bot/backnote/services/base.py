from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker


class BaseService:
    def __init__(self, sessionmaker: async_sessionmaker) -> None:
        self._sm = sessionmaker


def apply_fields(obj: Any, fields: dict[str, Any], allowed: set[str]) -> None:
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Fields not editable: {', '.join(sorted(unknown))}")
    for key, value in fields.items():
        setattr(obj, key, value)
