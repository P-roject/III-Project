import pytest
from fastapi.testclient import TestClient
from main import app
from database import get_db, engine, Base

# هر بار که تست اجرا میشه، جداول پاک و دوباره ساخته بشن
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


# override برای تست
def override_get_db():
    from database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="session")
def token():
    response = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return response.json()["access_token"]


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_01_login(token):
    assert token is not None


def test_02_create_parent(token):
    resp = client.post("/parents/", json={"name": "احمد محمدی", "phone_number": "09121234567"}, headers=headers(token))
    assert resp.status_code == 201
    return resp.json()["id"]


def test_03_create_class(token):
    resp = client.post("/classes/", json={"name": "ششم ب", "teacher_name": "آقای حسینی"}, headers=headers(token))
    assert resp.status_code == 201
    return resp.json()["id"]


def test_04_create_student(token):
    parent_id = test_02_create_parent(token)
    class_id = test_03_create_class(token)
    resp = client.post("/students/", json={
        "name": "محمد احمدی",
        "age": 12,
        "grade": 6,
        "parent_id": parent_id,
        "class_id": class_id
    }, headers=headers(token))
    assert resp.status_code == 201
    data = resp.json()
    assert data["parent"]["name"] == "احمد محمدی"
    assert data["class_"]["name"] == "ششم ب"


def test_05_age_validation(token):
    parent_id = test_02_create_parent(token)
    class_id = test_03_create_class(token)
    resp = client.post("/students/", json={
        "name": "بچه", "age": 4, "grade": 1,
        "parent_id": parent_id, "class_id": class_id
    }, headers=headers(token))

    # این جا اول 400 بود که توی تست ها دچار مشکل شد و استتوس کد رو تغییر دادم
    assert resp.status_code == 422


def test_06_soft_delete(token):
    parent_id = test_02_create_parent(token)
    class_id = test_03_create_class(token)
    student = client.post("/students/", json={
        "name": "حذف‌شونده", "age": 11, "grade": 5,
        "parent_id": parent_id, "class_id": class_id
    }, headers=headers(token)).json()
    client.delete(f"/students/{student['id']}", headers=headers(token))
    resp = client.get("/students/", headers=headers(token))
    assert student["id"] not in [s["id"] for s in resp.json() if s["is_active"]]


def test_07_no_token():
    resp = client.get("/students/")
    assert resp.status_code == 401
