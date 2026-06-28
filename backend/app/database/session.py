import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

db_url = settings.database_url

# Normalize PostgreSQL URL for SQLAlchemy's async psycopg driver if it uses a generic scheme.
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)

engine_kwargs = {
    "echo": False,
    "future": True,
    "pool_pre_ping": True,
}
if not db_url.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
        }
    )

# Create async engine with production pooling where the driver supports it.
engine = create_async_engine(db_url, **engine_kwargs)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager to safely retrieve database sessions.
    Useful for background tasks, CLI scripts, and LangGraph nodes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session context error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency injection provider to yield db session context.
    """
    async with get_db_context() as session:
        yield session
