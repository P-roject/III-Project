# Student/api/StudentApi.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from typing import List

from ..model import Student
from ..serializer.StudentSchema import StudentCreate, StudentUpdate, StudentResponse
from utils.database import get_db

# ایمپورت مدل‌های مرتبط (برای چک وجود)
from Parent.model import Parent
from Class.model import Class

router = APIRouter(prefix="/students", tags=["دانش‌آموزان"])


@router.post("/", response_model=StudentResponse, status_code=201)
async def create_student(payload: StudentCreate, db: AsyncSession = Depends(get_db)):
    # بررسی والد و کلاس فعال باشند
    parent = await db.get(Parent, payload.parent_id)
    if not parent or parent.deleted_at is not None:
        raise HTTPException(status_code=404, detail="والد پیدا نشد یا حذف شده است")

    cls = await db.get(Class, payload.class_id)
    if not cls or cls.deleted_at is not None:
        raise HTTPException(status_code=404, detail="کلاس پیدا نشد یا حذف شده است")

    student = Student(**payload.model_dump())
    db.add(student)
    await db.commit()
    await db.refresh(student, ["parent", "class_"])
    return student


@router.get("/", response_model=List[StudentResponse])
async def get_students(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.parent), selectinload(Student.class_))
        .where(Student.deleted_at.is_(None))  # فقط دانش‌آموزان حذف‌نشده
        .order_by(Student.id.desc())
    )
    return result.scalars().all()


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.parent), selectinload(Student.class_))
        .where(Student.id == student_id, Student.deleted_at.is_(None))
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="دانش‌آموز پیدا نشد یا حذف شده است")
    return student


@router.put("/{student_id}", response_model=StudentResponse)
@router.patch("/{student_id}", response_model=StudentResponse)
async def update_student(student_id: int, payload: StudentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.deleted_at.is_(None))
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="دانش‌آموز پیدا نشد یا حذف شده است")

    update_data = payload.model_dump(exclude_unset=True)

    if "parent_id" in update_data:
        p = await db.get(Parent, update_data["parent_id"])
        if not p or p.deleted_at is not None:
            raise HTTPException(status_code=400, detail="والد معتبر نیست یا حذف شده است")

    if "class_id" in update_data:
        c = await db.get(Class, update_data["class_id"])
        if not c or c.deleted_at is not None:
            raise HTTPException(status_code=400, detail="کلاس معتبر نیست یا حذف شده است")

    for key, value in update_data.items():
        setattr(student, key, value)

    await db.commit()
    await db.refresh(student, ["parent", "class_"])
    return student


@router.delete("/{student_id}", status_code=204)
async def soft_delete_student(student_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.deleted_at.is_(None))
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="دانش‌آموز پیدا نشد یا قبلاً حذف شده است")

    # Soft Delete کامل
    student.deleted_at = datetime.now(timezone.utc)
    student.is_active = False

    await db.commit()
    return None  # 204 No Content