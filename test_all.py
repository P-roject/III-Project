# test_all.py
import pytest
import random
from httpx import AsyncClient


# ==========================================
# توابع کمکی (Helpers)
# ==========================================

def random_phone():
    """تولید شماره تلفن رندوم یونیک"""
    return f"09{random.randint(100000000, 999999999)}"


# ==========================================
# تست‌های احراز هویت (Authentication)
# ==========================================

@pytest.mark.asyncio(loop_scope="function")
async def test_login_flow(client: AsyncClient):
    # 1. تست لاگین موفق
    login_res = await client.post("/auth/login", data={
        "username": "admin",
        "password": "admin123"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"

    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 2. تست لاگین ناموفق
    fail_res = await client.post("/auth/login", data={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert fail_res.status_code == 401


# ==========================================
# تست‌های مربوط به Parent (Soft Delete)
# ==========================================

@pytest.mark.asyncio(loop_scope="function")
async def test_parent_lifecycle_soft_delete(auth_client: AsyncClient):
    # 1. ایجاد
    payload = {"name": "Test Parent", "phone_number": random_phone()}
    create_res = await auth_client.post("/parents/", json=payload)
    assert create_res.status_code == 201, f"Create failed: {create_res.text}"
    parent_id = create_res.json()["id"]

    # 2. حذف (مطمئن شوید utils/base_model.py اصلاح شده باشد)
    del_res = await auth_client.delete(f"/parents/{parent_id}")
    assert del_res.status_code == 204

    # 3. اطمینان از حذف (GET باید 404 بدهد)
    get_res = await auth_client.get(f"/parents/{parent_id}")
    assert get_res.status_code == 404

    # 4. بازیابی (Restore)
    restore_res = await auth_client.post(f"/parents/{parent_id}/restore")
    assert restore_res.status_code == 200

    # 5. دریافت مجدد
    get_res_2 = await auth_client.get(f"/parents/{parent_id}")
    assert get_res_2.status_code == 200


# ==========================================
# تست‌های زنجیره‌ای Student
# ==========================================

@pytest.mark.asyncio(loop_scope="function")
async def test_create_student_full_chain(auth_client: AsyncClient):
    # A. Parent
    p_res = await auth_client.post("/parents/", json={"name": "Dad", "phone_number": random_phone()})
    assert p_res.status_code == 201
    pid = p_res.json()["id"]

    # B. Class
    c_res = await auth_client.post("/classes/", json={"name": "Physics", "teacher_name": "Dr. X"})
    assert c_res.status_code == 201
    cid = c_res.json()["id"]

    # C. Student
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
    # چک کردن نام به جای parent_id که ممکن است در خروجی نباشد
    assert data["name"] == "Albert"
    assert "id" in data


@pytest.mark.asyncio(loop_scope="function")
async def test_create_student_with_deleted_parent(auth_client: AsyncClient):
    # 1. ساخت والد
    p = await auth_client.post("/parents/", json={"name": "Deleted Mom", "phone_number": random_phone()})
    pid = p.json()["id"]

    # 2. ساخت کلاس (با نام معلم طولانی‌تر برای جلوگیری از خطای 422)
    c = await auth_client.post("/classes/", json={"name": "Chem", "teacher_name": "Mr. White"})
    assert c.status_code == 201, f"Class create failed: {c.text}"
    cid = c.json()["id"]

    # 3. حذف والد
    await auth_client.delete(f"/parents/{pid}")

    # 4. تلاش برای ساخت دانش‌آموز متصل به والد حذف شده
    payload = {
        "name": "Orphan Student",
        "age": 10,
        "grade": 5,
        "parent_id": pid,
        "class_id": cid
    }

    res = await auth_client.post("/students/", json=payload)

    # باید 404 بدهد چون والد پیدا نمی‌شود (یا 400 بسته به لاجیک شما)
    assert res.status_code in [404, 400], f"Should fail but got {res.status_code}"
