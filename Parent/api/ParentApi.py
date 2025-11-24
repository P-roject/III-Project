from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..model import Parent
from ..serializer.ParentSchema import ParentCreate, ParentUpdate, ParentResponse
from utils.database import get_db

router = APIRouter(prefix="/parents", tags=["parents"])


@router.post("/", response_model=ParentResponse, status_code=201)
async def create_parent(payload: ParentCreate, db: AsyncSession = Depends(get_db)):

    exists = await db.execute(
        select(Parent).where(
            Parent.phone_number == payload.phone_number,
            Parent.is_deleted.is_(False)
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Phone number already exists")

    parent = Parent(**payload.model_dump())
    db.add(parent)
    await db.commit()
    await db.refresh(parent)
    return parent


@router.get("/", response_model=List[ParentResponse])
async def get_parents(db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Parent)
        .where(Parent.is_deleted.is_(False))
        .order_by(Parent.id.desc())
    )
    return result.scalars().all()


@router.get("/{parent_id}", response_model=ParentResponse)
async def get_parent(parent_id: int, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Parent).where(Parent.id == parent_id, Parent.is_deleted.is_(False))
    )
    parent = result.scalar_one_or_none()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    return parent


@router.put("/{parent_id}", response_model=ParentResponse)
@router.patch("/{parent_id}", response_model=ParentResponse)
async def update_parent(parent_id: int, payload: ParentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Parent).where(Parent.id == parent_id, Parent.is_deleted.is_(False))
    )
    parent = result.scalar_one_or_none()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "phone_number" in update_data:
        exists = await db.execute(
            select(Parent).where(
                Parent.phone_number == update_data["phone_number"],
                Parent.id != parent_id,
                Parent.is_deleted.is_(False)
            )
        )
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Phone number already exists")

    for key, value in update_data.items():
        setattr(parent, key, value)

    await db.commit()
    await db.refresh(parent)
    return parent


@router.delete("/{parent_id}", status_code=204)
async def soft_delete_parent(parent_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Parent).where(Parent.id == parent_id, Parent.is_deleted.is_(False))
    )
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    await parent.soft_delete(db)

    return None


@router.post("/{parent_id}/restore", response_model=ParentResponse)
async def restore_parent(parent_id: int, db: AsyncSession = Depends(get_db)):
    """
    بازگردانی رکورد حذف شده (Restore)
    """
    result = await db.execute(select(Parent).where(Parent.id == parent_id))
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    if parent.is_deleted:
        await parent.restore(db)

    return parent
