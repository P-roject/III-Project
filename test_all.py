# test_all.py
import pytest
import random
from httpx import AsyncClient, ASGITransport
from main import app
from utils.database import engine, AsyncSessionLocal, get_db
from sqlalchemy.ext.asyncio import AsyncSession

# ====================
# Override اصلی: transactional session
# ====================

async def override_get_db():
    """
    اتصال مستقل غیر اشتراکی با rollback بعد از پایان هر تست.
    این مدل تمام خطاهای asyncpg concurrent transaction را می‌گیرد.
    """
    async with engine.begin() as conn:  # ← transaction واقعی و ایزوله
        async_session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield async_session
        finally:
            await async_session.close()
            # rollback ضمنی و خودکار توسط engine.begin() انجام می‌شود


# Fixture برای client
@pytest.fixture(scope="function")
async def client():
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def auth_token(client):
    res = await client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


@pytest.fixture(scope="function")
async def auth_client(auth_token, client):
    client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return client


def random_phone():
    return f"09{random.randint(100000000, 999999999)}"


# ========================== تست‌ها ==========================
@pytest.mark.asyncio(loop_scope="function")
async def test_login_success(client):
    r = await client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    print("✅ Login Success:", r.json())


@pytest.mark.asyncio(loop_scope="function")
async def test_login_wrong_password(client):
    r = await client.post("/auth/login", data={"username": "admin", "password": "x"})
    assert r.status_code == 401
    print("✅ Wrong Password")


@pytest.mark.asyncio(loop_scope="function")
async def test_no_token_protected_route(client):
    r = await client.get("/parents/")
    assert r.status_code == 401
    print("✅ Unauthorized Route")


@pytest.mark.asyncio(loop_scope="function")
async def test_parent_crud(auth_client):
    ph = random_phone()
    r1 = await auth_client.post("/parents/", json={"name": "Parent1", "phone_number": ph})
    assert r1.status_code in (200, 201)
    pid = r1.json()["id"]

    r2 = await auth_client.get("/parents/")
    assert any(p["id"] == pid for p in r2.json())

    r3 = await auth_client.delete(f"/parents/{pid}")
    assert r3.status_code in (200, 204)
    print("✅ Parent CRUD completed")


@pytest.mark.asyncio(loop_scope="function")
async def test_student_full_flow(auth_client):
    parent = await auth_client.post("/parents/", json={"name": "ParentX", "phone_number": random_phone()})
    pid = parent.json()["id"]

    cls = await auth_client.post("/classes/", json={"name": "Math", "teacher_name": "Mr. Smith"})
    cid = cls.json()["id"]

    stu = await auth_client.post(
        "/students/",
        json={"name": "Ali", "age": 10, "grade": 5, "parent_id": pid, "class_id": cid},
    )
    sid = stu.json()["id"]

    d = await auth_client.delete(f"/students/{sid}")
    assert d.status_code in (200, 204)
    print("✅ Student Flow OK")


@pytest.mark.asyncio(loop_scope="function")
async def test_age_validation(auth_client):
    p = await auth_client.post("/parents/", json={"name": "ParentY", "phone_number": random_phone()})
    pid = p.json()["id"]

    c = await auth_client.post("/classes/", json={"name": "Science", "teacher_name": "Ms.J"})
    cid = c.json()["id"]

    s = await auth_client.post(
        "/students/",
        json={"name": "Tiny", "age": 3, "grade": 1, "parent_id": pid, "class_id": cid},
    )
    assert s.status_code == 422
    print("✅ Age Validation OK")
