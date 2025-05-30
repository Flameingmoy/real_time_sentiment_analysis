# backend/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

if settings.DATABASE_URL:
    async_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False, # Set to True to log SQL queries, False for production
        pool_pre_ping=True # Checks connection health before use
    )

    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False # Recommended for FastAPI to access committed objects
    )
    logger.info("Async SQLAlchemy engine and session maker configured successfully.")
else:
    logger.error(
        "DATABASE_URL is not set in the environment. "
        "SQLAlchemy async engine and session maker cannot be configured. "
        "Database operations will fail."
    )
    async_engine = None
    AsyncSessionLocal = None # type: ignore

async def get_db() -> AsyncSession:
    """
    FastAPI dependency to get an async database session.
    Ensures the session is closed after the request.
    """
    if AsyncSessionLocal is None:
        logger.critical("AsyncSessionLocal is not initialized. Cannot provide DB session. DATABASE_URL might be missing.")
        raise RuntimeError("Database not configured. AsyncSessionLocal is None.")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # According to FastAPI/SQLAlchemy best practices for async,
            # explicit commit/rollback should happen in the CRUD operations or service layer,
            # not typically in the dependency itself unless it's a very simple app.
            # For now, we'll let the calling code handle commits.
            # If a commit is desired here after every successful request using the session:
            # await session.commit()
        except Exception:
            await session.rollback()
            raise
        # finally:
            # The 'async with' block handles closing the session.
            # await session.close() # Not strictly necessary with 'async with'
