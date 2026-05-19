"""Database session and engine configuration."""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

# Module-level singletons (lazy-loaded on first access)
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _init_db() -> None:
    """Initialize database engine and session factory (call once)."""
    global _engine, _session_factory
    if _engine is not None:
        return  # Already initialized
    
    from app.config import get_settings
    settings = get_settings()
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        future=True,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


class _LazyEngine:
    """Proxy object that initializes engine on first access."""
    def __getattr__(self, name: str):
        _init_db()
        assert _engine is not None
        return getattr(_engine, name)

    def __await__(self):
        _init_db()
        assert _engine is not None
        return _engine.__await__()


class _LazySessionFactory:
    """Proxy object that initializes session factory on first access."""
    def __call__(self):
        _init_db()
        assert _session_factory is not None
        return _session_factory()

    def __getattr__(self, name: str):
        _init_db()
        assert _session_factory is not None
        return getattr(_session_factory, name)


# Expose as module-level objects (lazy-loaded)
engine = _LazyEngine()
AsyncSessionLocal = _LazySessionFactory()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session for FastAPI routes."""
    _init_db()
    assert _session_factory is not None
    async with _session_factory() as session:
        yield session


async def check_database_connection() -> tuple[bool, int]:
    """
    Check database connectivity.

    Returns:
        Tuple of (is_connected, response_time_ms)
    """
    import time

    start = time.perf_counter()
    try:
        _init_db()
        assert _engine is not None
        async with _engine.begin() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return True, elapsed_ms
    except Exception:
        return False, 0


