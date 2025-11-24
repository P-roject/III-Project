# import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport
from main import app
from utils.database import Base, get_db

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:hack55@localhost:5432/school_fastapi_test"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def async_db():
    """ساخت دیتابیس تست"""
    async with test_engine.begin() as conn:
        print("\n------------ DEBUG TABLES ------------")
        print("Tables detected inside Base.metadata:", Base.metadata.tables.keys())
        print("--------------------------------------\n")

        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(async_db):
    async def override_get_db():
        yield async_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_token(client):
    login_res = await client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200, "Login failed in fixture"
    return login_res.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def auth_client(auth_token, client):
    client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return client
