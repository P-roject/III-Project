from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from utils.database import get_db
from ..model import Class
from ..serializer.ClassSchema import ClassCreate, ClassUpdate, ClassResponse


router = APIRouter(prefix="/classes", tags=["Classes"])


@router.post("/", response_model=ClassResponse, status_code=201)
async def create_class(payload: ClassCreate, db: AsyncSession = Depends(get_db)):
    db_class = Class(**payload.model_dump())
    db.add(db_class)
    await db.commit()
    await db.refresh(db_class)
    return db_class


@router.get("/", response_model=list[ClassResponse])
async def get_classes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Class).where(Class.is_active.is_(True)))
    return result.scalars().all()


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(class_id: int, db: AsyncSession = Depends(get_db)):
    cls = await db.get(Class, class_id)
    if not cls or not cls.is_active:
        raise HTTPException(status_code=404, detail="class not found")
    return cls


@router.put("/{class_id}", response_model=ClassResponse)
async def update_class(class_id: int, payload: ClassUpdate, db: AsyncSession = Depends(get_db)):
    cls = await db.get(Class, class_id)
    if not cls or not cls.is_active:
        raise HTTPException(status_code=404, detail="class not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cls, key, value)

    await db.commit()
    await db.refresh(cls)
    return cls


@router.patch("/{class_id}", response_model=ClassResponse)
async def patch_class(class_id: int, payload: ClassUpdate, db: AsyncSession = Depends(get_db)):
    return await update_class(class_id, payload, db)


@router.delete("/{class_id}", status_code=204)
async def soft_delete_class(class_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        update(Class)
        .where(Class.id == class_id, Class.is_active.is_(True))
        .values(is_active=False)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="class not found or has already been dropped")
    await db.commit()