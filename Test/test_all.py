import pytest
import random
import string
from httpx import AsyncClient

# === IMPORT MODELS TO REGISTER TABLES ===
# این ایمپورت‌ها ضروری هستند تا SQLAlchemy جداول را بشناسد
from Parent.model import Parent
from Class.model import Class
from Student.model import Student


# ========================================

# --- Helper Functions ---
def random_string(length=6):
    return ''.join(random.choices(string.ascii_letters, k=length))


def random_phone():
    # تولید شماره موبایل رندوم برای جلوگیری از ارور تکراری بودن
    return f"09{random.randint(100000000, 999999999)}"


# --- Tests ---

@pytest.mark.asyncio
async def test_01_login_success(client: AsyncClient):
    """تست دریافت توکن با نام کاربری و رمز صحیح"""
    payload = {"username": "admin", "password": "admin123"}
    response = await client.post("/auth/login", data=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_02_create_parent(auth_client: AsyncClient):
    """تست ساخت یک والد جدید"""
    payload = {
        "name": f"Parent_{random_string()}",
        "phone_number": random_phone()
    }
    response = await auth_client.post("/parents/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_03_create_class(auth_client: AsyncClient):
    """تست ساخت یک کلاس جدید"""
    payload = {
        "name": f"Class_{random_string()}",
        "teacher_name": f"Teacher_{random_string()}"
    }
    response = await auth_client.post("/classes/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]


@pytest.mark.asyncio
async def test_04_create_student_full_chain(auth_client: AsyncClient):
    """
    تست زنجیره‌ای:
    1. ساخت والد
    2. ساخت کلاس
    3. ساخت دانش‌آموز متصل به والد و کلاس
    4. بررسی لود شدن روابط در پاسخ
    """
    # 1. Create Parent
    p_payload = {"name": "P_Chain", "phone_number": random_phone()}
    p_res = await auth_client.post("/parents/", json=p_payload)
    parent_id = p_res.json()["id"]

    # 2. Create Class
    c_payload = {"name": "C_Chain", "teacher_name": "T_Chain"}
    c_res = await auth_client.post("/classes/", json=c_payload)
    class_id = c_res.json()["id"]

    # 3. Create Student
    s_payload = {
        "name": "Student_Chain",
        "age": 10,
        "grade": 5,
        "parent_id": parent_id,
        "class_id": class_id
    }
    s_res = await auth_client.post("/students/", json=s_payload)

    # Assertions
    assert s_res.status_code == 201
    data = s_res.json()
    assert data["name"] == "Student_Chain"
    # بررسی اینکه روابط Parent و Class درست لود شده باشند (نه Null)
    assert data["parent"]["id"] == parent_id
    assert data["class_"]["id"] == class_id


@pytest.mark.asyncio
async def test_05_get_students_list(auth_client: AsyncClient):
    """تست دریافت لیست دانش‌آموزان"""
    # ابتدا یک دانش‌آموز می‌سازیم
    p_res = await auth_client.post("/parents/", json={"name": "P1", "phone_number": random_phone()})
    s_payload = {"name": "S1", "age": 12, "grade": 6, "parent_id": p_res.json()["id"]}
    await auth_client.post("/students/", json=s_payload)

    # دریافت لیست
    response = await auth_client.get("/students/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_06_update_student_patch(auth_client: AsyncClient):
    """تست آپدیت جزئی (PATCH) نام دانش‌آموز"""
    # Setup
    p_res = await auth_client.post("/parents/", json={"name": "P_Edit", "phone_number": random_phone()})
    s_res = await auth_client.post("/students/",
                                   json={"name": "OldName", "age": 10, "grade": 4, "parent_id": p_res.json()["id"]})
    student_id = s_res.json()["id"]

    # Update Name
    patch_payload = {"name": "NewNameUpdated"}
    response = await auth_client.patch(f"/students/{student_id}", json=patch_payload)

    assert response.status_code == 200
    assert response.json()["name"] == "NewNameUpdated"
    assert response.json()["age"] == 10  # سن نباید تغییر کرده باشد


@pytest.mark.asyncio
async def test_07_create_student_validation_error(auth_client: AsyncClient):
    """تست اعتبارسنجی: تلاش برای ساخت دانش‌آموز با سن غیرمجاز"""
    invalid_payload = {
        "name": "Baby Student",
        "age": 2,  # سن زیر 6 سال مجاز نیست
        "grade": 1
    }
    response = await auth_client.post("/students/", json=invalid_payload)
    assert response.status_code == 422  # Validation Error


@pytest.mark.asyncio
async def test_08_soft_delete_parent_cascade(auth_client: AsyncClient):
    """
    تست حذف آبشاری (Cascade Soft Delete):
    با حذف والد، دانش‌آموز هم باید Soft Delete شود.
    """
    # Setup Chain
    p_res = await auth_client.post("/parents/", json={"name": "DelParent", "phone_number": random_phone()})
    parent_id = p_res.json()["id"]

    s_res = await auth_client.post("/students/",
                                   json={"name": "DelStudent", "age": 10, "grade": 4, "parent_id": parent_id})
    student_id = s_res.json()["id"]

    # Delete Parent
    del_res = await auth_client.delete(f"/parents/{parent_id}")
    assert del_res.status_code == 204

    # Check Parent is deleted (GET returns 200 but is_deleted=True based on your code)
    p_check = await auth_client.get(f"/parents/{parent_id}")
    assert p_check.status_code == 200
    assert p_check.json()["is_deleted"] is True

    # Check Student is ALSO deleted (Cascade)
    s_check = await auth_client.get(f"/students/{student_id}")
    assert s_check.status_code == 200
    assert s_check.json()["is_deleted"] is True


@pytest.mark.asyncio
async def test_09_restore_student_fails_if_parent_deleted(auth_client: AsyncClient):
    """
    تست منطق بازیابی:
    نمی‌توان دانش‌آموز را بازیابی کرد اگر والدش هنوز حذف شده باشد.
    """
    # Setup & Delete
    p_res = await auth_client.post("/parents/", json={"name": "GhostParent", "phone_number": random_phone()})
    parent_id = p_res.json()["id"]
    s_res = await auth_client.post("/students/",
                                   json={"name": "GhostStudent", "age": 10, "grade": 4, "parent_id": parent_id})
    student_id = s_res.json()["id"]

    await auth_client.delete(f"/parents/{parent_id}")  # This deletes student too

    # Try to Restore Student ONLY
    restore_res = await auth_client.post(f"/students/{student_id}/restore")

    # Expect Error 400 (Cannot restore student because their Parent is deleted)
    assert restore_res.status_code == 400
    assert "Parent is deleted" in restore_res.json()["detail"]


@pytest.mark.asyncio
async def test_10_full_restore_cycle(auth_client: AsyncClient):
    """
    تست چرخه کامل بازیابی:
    1. حذف والد (و دانش‌آموز)
    2. بازیابی والد
    3. بازیابی دانش‌آموز (الان باید موفق شود)
    """
    # Setup & Delete
    p_res = await auth_client.post("/parents/", json={"name": "ResParent", "phone_number": random_phone()})
    parent_id = p_res.json()["id"]
    s_res = await auth_client.post("/students/",
                                   json={"name": "ResStudent", "age": 10, "grade": 4, "parent_id": parent_id})
    student_id = s_res.json()["id"]

    await auth_client.delete(f"/parents/{parent_id}")

    # 1. Restore Parent
    await auth_client.post(f"/parents/{parent_id}/restore")

    # 2. Restore Student
    res_s = await auth_client.post(f"/students/{student_id}/restore")

    assert res_s.status_code == 200
    assert res_s.json()["is_deleted"] is False
    assert res_s.json()["is_active"] is True
