import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

Base = declarative_base()

# آدرس دیتابیس PostgreSQL اصلی
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:hack55@localhost:5432/school_fastapi"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
