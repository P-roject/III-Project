# Class/api/ClassApi.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from typing import List

from ..model import Class
from ..serializer.ClassSchema import ClassCreate, ClassUpdate, ClassResponse
from utils.database import get_db

router = APIRouter(prefix="/classes", tags=["کلاس‌ها"])


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
        .where(Class.deleted_at.is_(None))  # فقط کلاس‌های حذف‌نشده
        .order_by(Class.id.desc())
    )
    return result.scalars().all()


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(class_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.deleted_at.is_(None))
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=404, detail="کلاس پیدا نشد یا حذف شده است")
    return cls


@router.put("/{class_id}", response_model=ClassResponse)
@router.patch("/{class_id}", response_model=ClassResponse)
async def update_class(class_id: int, payload: ClassUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.deleted_at.is_(None))
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=404, detail="کلاس پیدا نشد یا حذف شده است")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cls, key, value)

    await db.commit()
    await db.refresh(cls)
    return cls


@router.delete("/{class_id}", status_code=204)
async def soft_delete_class(class_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.deleted_at.is_(None))
    )
    cls = result.scalar_one_or_none()

    if not cls:
        raise HTTPException(status_code=404, detail="کلاس پیدا نشد یا قبلاً حذف شده است")

    # Soft Delete کامل
    cls.deleted_at = datetime.now(timezone.utc)
    cls.is_active = False

    await db.commit()
    return None  # 204 No Content