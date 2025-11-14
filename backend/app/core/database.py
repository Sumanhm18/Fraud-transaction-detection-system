"""
Database configuration and initialization
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import structlog

from .config import get_settings

logger = structlog.get_logger()

# SQLAlchemy setup
Base = declarative_base()
metadata = MetaData()

# Global engine and session maker
engine = None
async_session_maker = None


async def init_db():
    """Initialize database connection"""
    global engine, async_session_maker
    
    settings = get_settings()
    
    try:
        # Create async engine
        engine = create_async_engine(
            settings.database_url,
            echo=settings.env == "development",
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
        )
        
        # Create session maker
        async_session_maker = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Test connection
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise


async def close_db():
    """Close database connections"""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session context manager"""
    if not async_session_maker:
        raise RuntimeError("Database not initialized")
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI routes"""
    async with get_db_session() as session:
        yield session