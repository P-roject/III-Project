from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from ..model import Class
from Student.model import Student
from ..serializer.ClassSchema import ClassCreate, ClassUpdate, ClassResponse
from Database.database import get_db
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/classes", tags=["classes"])


@router.post("/", response_model=ClassResponse, status_code=201)
async def create_class(payload: ClassCreate, db: AsyncSession = Depends(get_db)):
    db_class = Class(**payload.model_dump())
    db.add(db_class)
    await db.commit()
    await db.refresh(db_class)
    return db_class


@router.get("/", response_model=List[ClassResponse])
async def get_classes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Class)
        .options(selectinload(Class.students))
        .order_by(Class.id.desc())
    )
    return result.scalars().all()


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(class_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Class)
        .options(selectinload(Class.students))
        .where(Class.id == class_id)
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    return cls


@router.patch("/{class_id}", response_model=ClassResponse)
async def update_class_partial(class_id: int, payload: ClassUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Class).where(Class.id == class_id, Class.is_deleted.is_(False)))
    db_class = result.scalars().first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    update_data = payload.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_class, key, value)

    await db.commit()
    await db.refresh(db_class)
    return db_class


@router.put("/{class_id}", response_model=ClassResponse)
async def update_class_full(class_id: int, payload: ClassUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Class).where(Class.id == class_id, Class.is_deleted.is_(False)))
    db_class = result.scalars().first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    update_data = payload.model_dump(exclude_unset=False)

    if update_data.get("name") is None or update_data.get("teacher_name") is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name and Teacher Name are required for PUT request."
        )

    for key, value in update_data.items():
        setattr(db_class, key, value)

    await db.commit()
    await db.refresh(db_class)
    return db_class


@router.delete("/{class_id}", status_code=204)
async def soft_delete_class(class_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.is_deleted.is_(False))
    )
    cls = result.scalar_one_or_none()

    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    await cls.soft_delete(db)

    # Cascade Soft Delete
    students_result = await db.execute(
        select(Student).where(Student.class_id == class_id, Student.is_deleted.is_(False))
    )
    students = students_result.scalars().all()

    for student in students:
        await student.soft_delete(db)

    return None


@router.post("/{class_id}/restore", response_model=ClassResponse)
async def restore_class(class_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Class)
        .options(selectinload(Class.students))  # لود کردن برای پاسخ نهایی
        .where(Class.id == class_id)
    )
    cls = result.scalar_one_or_none()

    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    if cls.is_deleted:
        # 1. بازیابی کلاس
        await cls.restore(db)

        # 2. بازیابی خودکار دانش‌آموزان زیرمجموعه (Cascading Restore)
        students_result = await db.execute(
            select(Student).where(Student.class_id == class_id, Student.is_deleted.is_(True))
        )
        deleted_students = students_result.scalars().all()

        for student in deleted_students:
            await student.restore(db)

        await db.commit()  # کامیت نهایی برای کلاس و همه دانش‌آموزان
        await db.refresh(cls)

    return cls
