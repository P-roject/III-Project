import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Base مشترک برای مدل‌ها
Base = declarative_base()

# انتخاب دیتابیس بر اساس محیط
# در حالت تست از SQLite in-memory استفاده می‌کنیم
# در حالت عادی (اجرا با uvicorn یا اپ) از PostgreSQL
DATABASE_URL = (
    "sqlite+aiosqlite:///:memory:"
    if os.getenv("TESTING")
    else "postgresql+asyncpg://postgres:hack55@localhost/school_fastapi"
)

# ساخت Engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

# ساخت Session factory
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


# -------------------------------
#  تابع اصلی برای Dependency Injection در FastAPI
# -------------------------------
async def get_db():
    """
    Dependency for FastAPI endpoints.
    Yields an async SQLAlchemy session.
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
