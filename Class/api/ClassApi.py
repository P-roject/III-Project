# Class/api/ClassApi.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..model import Class
from ..serializer.ClassSchema import ClassCreate, ClassUpdate, ClassResponse
from utils.database import get_db

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
    # اصلاح شده: شرط بر اساس is_deleted است، نه deleted_at
    result = await db.execute(
        select(Class)
        .where(Class.is_deleted.is_(False))
        .order_by(Class.id.desc())
    )
    return result.scalars().all()


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(class_id: int, db: AsyncSession = Depends(get_db)):
    # اصلاح شده: شرط بر اساس is_deleted است
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.is_deleted.is_(False))
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    return cls


@router.put("/{class_id}", response_model=ClassResponse)
@router.patch("/{class_id}", response_model=ClassResponse)
async def update_class(class_id: int, payload: ClassUpdate, db: AsyncSession = Depends(get_db)):
    # اصلاح شده: شرط بر اساس is_deleted است
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.is_deleted.is_(False))
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cls, key, value)

    await db.commit()
    await db.refresh(cls)
    return cls


@router.delete("/{class_id}", status_code=204)
async def soft_delete_class(class_id: int, db: AsyncSession = Depends(get_db)):
    # اصلاح شده: پیدا کردن رکورد فعال برای حذف
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.is_deleted.is_(False))
    )
    cls = result.scalar_one_or_none()

    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    # استفاده از متد متمرکز Soft Delete
    await cls.soft_delete(db)

    return None


@router.post("/{class_id}/restore", response_model=ClassResponse)
async def restore_class(class_id: int, db: AsyncSession = Depends(get_db)):
    """
    بازگردانی رکورد حذف شده (Restore)
    """
    # اینجا همه رکوردها (چه حذف شده چه نشده) را می‌گیریم
    result = await db.execute(select(Class).where(Class.id == class_id))
    cls = result.scalar_one_or_none()

    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    # فقط اگر واقعاً حذف شده است (is_deleted=True) بازیابی می‌کنیم
    if cls.is_deleted:
        await cls.restore(db)

    # نکته: اگر رکورد از قبل فعال باشد، تغییری نمی‌کند و همان برگردانده می‌شود

    return cls
