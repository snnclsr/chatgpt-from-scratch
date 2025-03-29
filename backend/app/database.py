from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from contextlib import contextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from typing import AsyncGenerator

# Get the directory where this file is located
BASEDIR = os.path.abspath(os.path.dirname(__file__))

# Create the SQLite URL (synchronous)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASEDIR, 'chat.db')}"

# Create the async SQLite URL
ASYNC_SQLALCHEMY_DATABASE_URL = (
    f"sqlite+aiosqlite:///{os.path.join(BASEDIR, 'chat.db')}"
)

# Create synchronous engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create async engine
async_engine = create_async_engine(
    ASYNC_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create SessionLocal class (synchronous)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create AsyncSessionLocal class
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Base class for models
Base = declarative_base()


@contextmanager
def get_db_context():
    """Context manager for database sessions.

    Usage:
        with get_db_context() as db:
            # use db session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
