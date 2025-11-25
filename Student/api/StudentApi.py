from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from ..model import Student
from ..serializer.StudentSchema import StudentCreate, StudentUpdate, StudentResponse
from Database.database import get_db
from Parent.model import Parent
from Class.model import Class

router = APIRouter(prefix="/students", tags=["students"])


async def get_student_with_relations(db: AsyncSession, student_id: int):
    """
    یک تابع کمکی برای دریافت دانش‌آموز به همراه تمام روابط
    """
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.parent), selectinload(Student.class_))
        .where(Student.id == student_id)
    )
    return result.scalar_one_or_none()


@router.post("/", response_model=StudentResponse, status_code=201)
async def create_student(payload: StudentCreate, db: AsyncSession = Depends(get_db)):
    if payload.parent_id:
        parent = await db.get(Parent, payload.parent_id)
        if not parent or parent.is_deleted:
            raise HTTPException(status_code=404, detail="Parent not found or deleted")

    if payload.class_id:
        cls = await db.get(Class, payload.class_id)
        if not cls or cls.is_deleted:
            raise HTTPException(status_code=404, detail="Class not found or deleted")

    student = Student(**payload.model_dump())
    db.add(student)
    await db.commit()

    # جهت اطمینان از لود شدن صحیح روابط در لحظه ساخت
    db.expire(student)
    refreshed_student = await get_student_with_relations(db, student.id)
    return refreshed_student


@router.get("/", response_model=List[StudentResponse])
async def get_students(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.parent), selectinload(Student.class_))
        .where(Student.is_deleted.is_(False))
        .order_by(Student.id.desc())
    )
    return result.scalars().all()


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    student = await get_student_with_relations(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.patch("/{student_id}", response_model=StudentResponse)
async def update_student_partial(student_id: int, payload: StudentUpdate, db: AsyncSession = Depends(get_db)):
    # 1. پیدا کردن دانش‌آموز
    student = await get_student_with_relations(db, student_id)
    if not student or student.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    update_data = payload.model_dump(exclude_unset=True)

    # 2. بررسی اعتبارسنجی
    if "parent_id" in update_data and update_data["parent_id"] is not None:
        parent_result = await db.execute(
            select(Parent).where(Parent.id == update_data["parent_id"], Parent.is_deleted.is_(False)))
        if not parent_result.scalars().first():
            raise HTTPException(status_code=404, detail="Parent not found")

    if "class_id" in update_data and update_data["class_id"] is not None:
        class_result = await db.execute(
            select(Class).where(Class.id == update_data["class_id"], Class.is_deleted.is_(False)))
        if not class_result.scalars().first():
            raise HTTPException(status_code=404, detail="Class not found")

    # 3. اعمال تغییرات
    for key, value in update_data.items():
        setattr(student, key, value)

    await db.commit()

    # === اصلاح مهم برای نمایش روابط ===
    # آبجکت فعلی در مموری پایتون هنوز روابط قدیمی (یا نال) را دارد.
    # با این دستور به SQLAlchmey می‌گوییم این آبجکت را "منقضی" کن.
    db.expire(student)

    # حالا دوباره از دیتابیس می‌خوانیم تا روابط جدید (parent/class) لود شوند
    refreshed_student = await get_student_with_relations(db, student_id)
    return refreshed_student


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student_full(student_id: int, payload: StudentUpdate, db: AsyncSession = Depends(get_db)):
    student = await get_student_with_relations(db, student_id)
    if not student or student.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    update_data = payload.model_dump(exclude_unset=False)

    required_fields = ["name", "age", "grade"]
    for field in required_fields:
        if update_data.get(field) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Field '{field}' cannot be null in a PUT request."
            )

    if update_data.get("parent_id") is not None:
        parent_result = await db.execute(
            select(Parent).where(Parent.id == update_data["parent_id"], Parent.is_deleted.is_(False)))
        if not parent_result.scalars().first():
            raise HTTPException(status_code=404, detail="Parent not found")

    if update_data.get("class_id") is not None:
        class_result = await db.execute(
            select(Class).where(Class.id == update_data["class_id"], Class.is_deleted.is_(False)))
        if not class_result.scalars().first():
            raise HTTPException(status_code=404, detail="Class not found")

    for key, value in update_data.items():
        setattr(student, key, value)

    await db.commit()

    # === اصلاح مهم ===
    db.expire(student)
    refreshed_student = await get_student_with_relations(db, student_id)
    return refreshed_student


@router.delete("/{student_id}", status_code=204)
async def soft_delete_student(student_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.is_deleted.is_(False))
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    await student.soft_delete(db)
    return None


@router.post("/{student_id}/restore", response_model=StudentResponse)
async def restore_student(student_id: int, db: AsyncSession = Depends(get_db)):
    student = await get_student_with_relations(db, student_id)

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if student.is_deleted:
        if student.parent and student.parent.is_deleted:
            raise HTTPException(status_code=400, detail="Cannot restore student because their Parent is deleted.")

        if student.class_ and student.class_.is_deleted:
            raise HTTPException(status_code=400, detail="Cannot restore student because their Class is deleted.")

        await student.restore(db)

        # برای restore هم بهتر است رفرش کنیم تا تاریخ‌های آپدیت شده درست برگردند
        db.expire(student)
        return await get_student_with_relations(db, student_id)

    return student