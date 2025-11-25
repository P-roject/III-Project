from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..model import Class
# ایمپورت کردن مدل Student برای حذف آبشاری
from Student.model import Student
from ..serializer.ClassSchema import ClassCreate, ClassUpdate, ClassResponse
from Database.database import get_db

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
        .where(Class.is_deleted.is_(False))
        .order_by(Class.id.desc())
    )
    return result.scalars().all()


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(class_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.is_deleted.is_(False))
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    return cls


@router.patch("/{class_id}", response_model=ClassResponse)
async def patch_class(class_id: int, payload: ClassUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.is_deleted.is_(False))
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    # Partial update
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cls, key, value)

    await db.commit()
    await db.refresh(cls)
    return cls


@router.put("/{class_id}", response_model=ClassResponse)
async def put_class(class_id: int, payload: ClassUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.is_deleted.is_(False))
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    # Full update
    update_data = payload.model_dump()
    for key, value in update_data.items():
        setattr(cls, key, value)

    await db.commit()
    await db.refresh(cls)
    return cls


@router.delete("/{class_id}", status_code=204)
async def soft_delete_class(class_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Find Class
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.is_deleted.is_(False))
    )
    cls = result.scalar_one_or_none()

    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    # 2. Soft Delete Class
    await cls.soft_delete(db)

    # 3. Cascade Soft Delete: Find and delete associated students
    students_result = await db.execute(
        select(Student).where(Student.class_id == class_id, Student.is_deleted.is_(False))
    )
    students = students_result.scalars().all()

    for student in students:
        await student.soft_delete(db)

    return None


@router.post("/{class_id}/restore", response_model=ClassResponse)
async def restore_class(class_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Class).where(Class.id == class_id))
    cls = result.scalar_one_or_none()

    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    if cls.is_deleted:
        await cls.restore(db)

    return cls
