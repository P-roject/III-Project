import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from utils.database import engine, Base


# این خط باعث میشه همه تست‌های این فایل async باشن
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def client():
    transport = ASGITransport(app=app, lifespan="on")
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_token(client):
    resp = await client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
async def auth_client(client, auth_token):
    client.headers = {"Authorization": f"Bearer {auth_token}"}
    yield client


async def test_login_success(client):
    resp = await client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client):
    resp = await client.post("/auth/login", data={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


async def test_no_token_protected_route(client):
    resp = await client.get("/parents/")
    assert resp.status_code == 401


async def test_parent_crud(auth_client):
    resp = await auth_client.post("/parents/", json={"name": "parent test", "phone_number": "09123456789"})
    assert resp.status_code == 201
    parent_id = resp.json()["id"]

    resp = await auth_client.get(f"/parents/{parent_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "parent test"


async def test_student_full_flow(auth_client):
    p = await auth_client.post("/parents/", json={"name": "test parent", "phone_number": "09990011223"})
    c = await auth_client.post("/classes/", json={"name": "12", "teacher_name": "teacherName"})

    resp = await auth_client.post("/students/", json={
        "name": "علی تست", "age": 18, "grade": 12,
        "parent_id": p.json()["id"], "class_id": c.json()["id"]
    })
    assert resp.status_code == 201
    student_id = resp.json()["id"]
    assert resp.json()["parent"]["name"] == "parent test"
    assert resp.json()["class_"]["name"] == "12"


    resp = await auth_client.delete(f"/students/{student_id}")
    assert resp.status_code == 204


    resp = await auth_client.get("/students/")
    assert student_id not in [s["id"] for s in resp.json()]


async def test_age_validation(auth_client):
    p = await auth_client.post("/parents/", json={"name": "test", "phone_number": "09000000001"})
    c = await auth_client.post("/classes/", json={"name": "test", "teacher_name": "test"})

    resp = await auth_client.post("/students/", json={
        "name": "کودک", "age": 4, "grade": 1,
        "parent_id": p.json()["id"], "class_id": c.json()["id"]
    })
    assert resp.status_code == 422


@pytest.fixture(scope="session", autouse=True)
async def prepare_db():
    # دقیقاً همان کاری که lifespan انجام می‌دهد، ولی فقط برای تست
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
