"""Test database adapter wrapping a synchronous SQLite session with async methods.

Enables isolated in-memory SQLite testing for FastAPI async session dependencies.
"""
from typing import Any
from sqlalchemy.orm import Session


class _NestedTransactionAdapter:
    """Async context manager wrapping a synchronous SQLAlchemy nested transaction (savepoint)."""

    def __init__(self, nested_tx: Any) -> None:
        self._tx = nested_tx

    async def __aenter__(self) -> Any:
        self._tx.__enter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        return self._tx.__exit__(exc_type, exc_val, exc_tb)


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

    def begin_nested(self) -> _NestedTransactionAdapter:
        return _NestedTransactionAdapter(self._sync.begin_nested())

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        return self._sync.execute(statement, *args, **kwargs)

    async def scalar(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        return self._sync.scalar(statement, *args, **kwargs)

