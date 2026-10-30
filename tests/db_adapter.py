"""Test database adapter wrapping a synchronous SQLite session with async methods.

Enables isolated in-memory SQLite testing for FastAPI async session dependencies.
"""
from typing import Any
from sqlalchemy.orm import Session


class AsyncSessionAdapter:
    """Adapts a synchronous SQLAlchemy Session for async/await calls."""

    def __init__(self, sync_session: Session) -> None:
        self._sync = sync_session

    def add(self, instance: Any) -> None:
        self._sync.add(instance)

    def add_all(self, instances: Any) -> None:
        self._sync.add_all(instances)

    def delete(self, instance: Any) -> None:
        self._sync.delete(instance)

    async def flush(self) -> None:
        self._sync.flush()

    async def commit(self) -> None:
        self._sync.commit()

    async def rollback(self) -> None:
        self._sync.rollback()

    async def refresh(self, instance: Any) -> None:
        self._sync.refresh(instance)

    async def close(self) -> None:
        self._sync.close()

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        return self._sync.execute(statement, *args, **kwargs)

    async def scalar(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        return self._sync.scalar(statement, *args, **kwargs)

