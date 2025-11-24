# Student/api/StudentApi.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from ..model import Student
from ..serializer.StudentSchema import StudentCreate, StudentUpdate, StudentResponse
from utils.database import get_db
from Parent.model import Parent
from Class.model import Class

router = APIRouter(prefix="/students", tags=["students"])


@router.post("/", response_model=StudentResponse, status_code=201)
async def create_student(payload: StudentCreate, db: AsyncSession = Depends(get_db)):
    # بررسی اینکه والد و کلاس وجود داشته باشند و حذف نشده باشند
    # نکته: متد get به تنهایی کافی نیست چون باید is_deleted را هم چک کنیم
    parent = await db.get(Parent, payload.parent_id)
    if not parent or parent.is_deleted:
        raise HTTPException(status_code=404, detail="Parent not found or deleted")

    cls = await db.get(Class, payload.class_id)
    if not cls or cls.is_deleted:
        raise HTTPException(status_code=404, detail="Class not found or deleted")

    student = Student(**payload.model_dump())
    db.add(student)
    await db.commit()
    # بارگذاری روابط برای پاسخ
    await db.refresh(student, ["parent", "class_"])
    return student


@router.get("/", response_model=List[StudentResponse])
async def get_students(db: AsyncSession = Depends(get_db)):
    # اصلاح شده: استفاده از is_deleted
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.parent), selectinload(Student.class_))
        .where(Student.is_deleted.is_(False))
        .order_by(Student.id.desc())
    )
    return result.scalars().all()


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    # اصلاح شده: استفاده از is_deleted
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.parent), selectinload(Student.class_))
        .where(Student.id == student_id, Student.is_deleted.is_(False))
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.put("/{student_id}", response_model=StudentResponse)
@router.patch("/{student_id}", response_model=StudentResponse)
async def update_student(student_id: int, payload: StudentUpdate, db: AsyncSession = Depends(get_db)):
    # پیدا کردن دانش‌آموز فعال با استفاده از is_deleted
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.parent), selectinload(Student.class_))
        .where(Student.id == student_id, Student.is_deleted.is_(False))
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    update_data = payload.model_dump(exclude_unset=True)

    # اگر والد تغییر کرد، چک کنیم والد جدید حذف نشده باشد
    if "parent_id" in update_data:
        p = await db.get(Parent, update_data["parent_id"])
        if not p or p.is_deleted:
            raise HTTPException(status_code=400, detail="Invalid parent_id or parent is deleted")

    # اگر کلاس تغییر کرد، چک کنیم کلاس جدید حذف نشده باشد
    if "class_id" in update_data:
        c = await db.get(Class, update_data["class_id"])
        if not c or c.is_deleted:
            raise HTTPException(status_code=400, detail="Invalid class_id or class is deleted")

    for key, value in update_data.items():
        setattr(student, key, value)

    await db.commit()
    await db.refresh(student, ["parent", "class_"])
    return student


@router.delete("/{student_id}", status_code=204)
async def soft_delete_student(student_id: int, db: AsyncSession = Depends(get_db)):
    # اصلاح شده: استفاده از is_deleted
    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.is_deleted.is_(False))
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Soft Delete استاندارد
    await student.soft_delete(db)

    return None


@router.post("/{student_id}/restore", response_model=StudentResponse)
async def restore_student(student_id: int, db: AsyncSession = Depends(get_db)):
    """
    بازگردانی دانش‌آموز حذف شده.
    شرط: والدین و کلاس او باید هنوز فعال باشند.
    """
    # لود کردن دانش‌آموز (همه رکوردها) به همراه روابط
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.parent), selectinload(Student.class_))
        .where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # اگر قبلاً حذف شده، فرآیند بازیابی شروع شود
    if student.is_deleted:
        # چک کردن سلامت وابستگی‌ها قبل از بازیابی
        if student.parent and student.parent.is_deleted:
            raise HTTPException(status_code=400, detail="Cannot restore student because their Parent is deleted.")

        if student.class_ and student.class_.is_deleted:
            raise HTTPException(status_code=400, detail="Cannot restore student because their Class is deleted.")

        await student.restore(db)

    return student
