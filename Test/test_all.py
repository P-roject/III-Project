import pytest
import random
from httpx import AsyncClient


# تابع کمکی برای تولید شماره موبایل تصادفی
def random_phone():
    return f"09{random.randint(100000000, 999999999)}"


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


@pytest.mark.asyncio(loop_scope="function")
async def test_parent_lifecycle_soft_delete(auth_client: AsyncClient):
    """
    این تست چرخه حیات والد (ساخت، حذف، بررسی حذف، بازیابی) را چک می‌کند.
    نکته: الان که API را اصلاح کردیم، وقتی والد حذف شده باشد، GET باید 404 بدهد.
    """
    # 1. ساخت والد
    payload = {"name": "Test Parent", "phone_number": random_phone()}
    create_res = await auth_client.post("/parents/", json=payload)
    assert create_res.status_code == 201, f"Create failed: {create_res.text}"
    parent_id = create_res.json()["id"]

    # 2. حذف والد
    del_res = await auth_client.delete(f"/parents/{parent_id}")
    assert del_res.status_code == 204

    # 3. دریافت والد حذف شده (باید 404 بدهد طبق تغییرات جدید API)
    get_res = await auth_client.get(f"/parents/{parent_id}")
    assert get_res.status_code == 404

    # 4. بازیابی والد (Restore)
    # توجه: مطمئن شوید متد restore در ParentApi.py وجود دارد
    restore_res = await auth_client.post(f"/parents/{parent_id}/restore")
    assert restore_res.status_code == 200

    # 5. دریافت مجدد (باید 200 بدهد)
    get_res_2 = await auth_client.get(f"/parents/{parent_id}")
    assert get_res_2.status_code == 200


@pytest.mark.asyncio(loop_scope="function")
async def test_create_student_full_chain(auth_client: AsyncClient):
    """
    این تست ساخت کامل دانش‌آموز با روابط را چک می‌کند.
    همچنین بررسی می‌کند که روابط (Parent/Class) در پاسخ جیسون وجود داشته باشند
    (که نشان‌دهنده رفع باگ ارور 500 و MissingGreenlet است).
    """
    # 1. ساخت والد
    p_res = await auth_client.post("/parents/", json={"name": "Dad", "phone_number": random_phone()})
    assert p_res.status_code == 201
    pid = p_res.json()["id"]

    # 2. ساخت کلاس
    c_res = await auth_client.post("/classes/", json={"name": "Physics", "teacher_name": "Dr. X"})
    assert c_res.status_code == 201
    cid = c_res.json()["id"]

    # 3. ساخت دانش‌آموز
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

    # === تست‌های اضافی برای اطمینان از لود شدن روابط ===
    # اگر اینجا ارور داد یعنی مشکل سریالایزر یا لود دیتابیس هنوز هست
    assert data["parent"]["id"] == pid
    assert data["class_"]["id"] == cid


@pytest.mark.asyncio(loop_scope="function")
async def test_create_student_with_deleted_parent(auth_client: AsyncClient):
    """
    تست جلوگیری از انتساب دانش‌آموز به والد حذف شده.
    """
    # 1. ساخت والد و کلاس
    p = await auth_client.post("/parents/", json={"name": "Deleted Mom", "phone_number": random_phone()})
    pid = p.json()["id"]

    c = await auth_client.post("/classes/", json={"name": "Chem", "teacher_name": "Mr. White"})
    cid = c.json()["id"]

    # 2. حذف والد
    await auth_client.delete(f"/parents/{pid}")

    # 3. تلاش برای ساخت دانش‌آموز با والد حذف شده
    payload = {
        "name": "Orphan Student",
        "age": 10,
        "grade": 5,
        "parent_id": pid,
        "class_id": cid
    }

    res = await auth_client.post("/students/", json=payload)

    # باید ارور 404 بدهد (چون در کد گفتیم اگر والد deleted بود raise 404)
    assert res.status_code in [404, 400], f"Should fail but got {res.status_code}"
