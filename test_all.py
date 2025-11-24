import pytest
import random
from httpx import AsyncClient


def random_phone():
    """تولید شماره تلفن رندوم یونیک"""
    return f"09{random.randint(100000000, 999999999)}"


@pytest.mark.asyncio(loop_scope="function")
async def test_login_flow(client: AsyncClient):
    login_res = await client.post("/auth/login", data={
        "username": "admin",
        "password": "admin123"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"

    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    fail_res = await client.post("/auth/login", data={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert fail_res.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_parent_lifecycle_soft_delete(auth_client: AsyncClient):
    payload = {"name": "Test Parent", "phone_number": random_phone()}
    create_res = await auth_client.post("/parents/", json=payload)
    assert create_res.status_code == 201, f"Create failed: {create_res.text}"
    parent_id = create_res.json()["id"]

    del_res = await auth_client.delete(f"/parents/{parent_id}")
    assert del_res.status_code == 204

    get_res = await auth_client.get(f"/parents/{parent_id}")
    assert get_res.status_code == 404

    restore_res = await auth_client.post(f"/parents/{parent_id}/restore")
    assert restore_res.status_code == 200

    get_res_2 = await auth_client.get(f"/parents/{parent_id}")
    assert get_res_2.status_code == 200


@pytest.mark.asyncio(loop_scope="function")
async def test_create_student_full_chain(auth_client: AsyncClient):
    p_res = await auth_client.post("/parents/", json={"name": "Dad", "phone_number": random_phone()})
    assert p_res.status_code == 201
    pid = p_res.json()["id"]

    c_res = await auth_client.post("/classes/", json={"name": "Physics", "teacher_name": "Dr. X"})
    assert c_res.status_code == 201
    cid = c_res.json()["id"]

    stu_payload = {
        "name": "Albert",
        "age": 15,
        "grade": 9,
        "parent_id": pid,
        "class_id": cid
    }
    s_res = await auth_client.post("/students/", json=stu_payload)
    assert s_res.status_code == 201, f"Student create failed: {s_res.text}"

    data = s_res.json()
    assert data["name"] == "Albert"
    assert "id" in data


@pytest.mark.asyncio(loop_scope="function")
async def test_create_student_with_deleted_parent(auth_client: AsyncClient):
    p = await auth_client.post("/parents/", json={"name": "Deleted Mom", "phone_number": random_phone()})
    pid = p.json()["id"]

    c = await auth_client.post("/classes/", json={"name": "Chem", "teacher_name": "Mr. White"})
    assert c.status_code == 201, f"Class create failed: {c.text}"
    cid = c.json()["id"]

    await auth_client.delete(f"/parents/{pid}")

    payload = {
        "name": "Orphan Student",
        "age": 10,
        "grade": 5,
        "parent_id": pid,
        "class_id": cid
    }

    res = await auth_client.post("/students/", json=payload)

    assert res.status_code in [404, 400], f"Should fail but got {res.status_code}"
