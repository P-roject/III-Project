import os
import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from utils.database import Base, engine
from datetime import datetime

os.environ["TESTING"] = "True"
pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(scope="session")
async def prepare_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(prepare_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_token(client):
    form_data = {"username": "admin", "password": "admin123"}
    r = await client.post("/auth/login", data=form_data)
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture
async def auth_client(auth_token, client):
    client.headers = {"Authorization": f"Bearer {auth_token}"}
    return client


async def test_login_success(client):
    response = await client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    print("Login Success ✅", response.json())


async def test_login_wrong_password(client):
    response = await client.post("/auth/login", data={"username": "admin", "password": "wrongpass"})
    assert response.status_code == 401
    print("Login Wrong Password ✅")


async def test_no_token_protected_route(client):
    response = await client.get("/parents/")
    assert response.status_code == 401
    print("Unauthorized Protected Route ✅")


async def test_parent_crud(auth_client):
    resp = await auth_client.post("/parents/", json={"name": "parent test", "phone_number": "09123456789"})
    assert resp.status_code in (200, 201)
    parent_id = resp.json()["id"]

    resp2 = await auth_client.get("/parents/")
    assert resp2.status_code == 200
    parents_list = resp2.json()
    assert any(p["id"] == parent_id for p in parents_list)

    resp3 = await auth_client.delete(f"/parents/{parent_id}")
    assert resp3.status_code in (200, 204)
    print("Parent CRUD ✅")


async def test_student_full_flow(auth_client):
    p = await auth_client.post("/parents/", json={"name": "parent test", "phone_number": "09990011223"})
    assert p.status_code in (200, 201)
    parent_id = p.json()["id"]

    # ✅ حالا داده کامل برای کلاس با دو فیلد ضروری
    c = await auth_client.post("/classes/", json={"name": "Math", "teacher_name": "Mr. Smith"})
    assert c.status_code in (200, 201)
    class_id = c.json()["id"]

    s = await auth_client.post(
        "/students/",
        json={
            "name": "student test",
            "age": 10,
            "grade": "5",
            "parent_id": parent_id,
            "class_id": class_id,
        },
    )
    assert s.status_code in (200, 201)
    student_id = s.json()["id"]

    d = await auth_client.delete(f"/students/{student_id}")
    assert d.status_code in (200, 204)

    check = await auth_client.get("/students/")
    assert check.status_code == 200
    assert all(st["id"] != student_id for st in check.json())
    print("Student Flow ✅")


async def test_age_validation(auth_client):
    p = await auth_client.post("/parents/", json={"name": "test", "phone_number": "09000000001"})
    assert p.status_code in (200, 201)
    parent_id = p.json()["id"]

    # ✅ اضافه کردن فیلد teacher_name
    c = await auth_client.post("/classes/", json={"name": "Science", "teacher_name": "Ms. Johnson"})
    assert c.status_code in (200, 201)
    class_id = c.json()["id"]

    invalid = {
        "name": "student invalid age",
        "age": 3,
        "grade": "1",
        "parent_id": parent_id,
        "class_id": class_id,
    }

    resp = await auth_client.post("/students/", json=invalid)
    assert resp.status_code == 422
    print("Age Validation ✅")
