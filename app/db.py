"""Подключение к БД. В проде — PostgreSQL, локально по умолчанию — SQLite-файл."""
import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")

# Небольшой пул: один воркер на общем сервере не должен занимать все соединения Postgres.
POOL = {} if DATABASE_URL.startswith("sqlite") else {"pool_size": 5, "max_overflow": 5, "pool_recycle": 1800}

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, **POOL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
