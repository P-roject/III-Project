from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from utils.database import get_db
from ..model import Parent
from ..serializer.ParentSchema import ParentCreate, ParentUpdate, ParentResponse

router = APIRouter(prefix="/parents", tags=["Parents"])


@router.post("/", response_model=ParentResponse, status_code=201)
async def create_parent(payload: ParentCreate, db: AsyncSession = Depends(get_db)):
    # چک تکراری نبودن شماره
    exists = await db.execute(select(Parent).where(Parent.phone_number == payload.phone_number))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="phone number already exists")

    parent = Parent(**payload.model_dump())
    db.add(parent)
    await db.commit()
    await db.refresh(parent)
    return parent


@router.get("/", response_model=list[ParentResponse])
async def get_parents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Parent).where(Parent.is_active.is_(True)))
    return result.scalars().all()


@router.get("/{parent_id}", response_model=ParentResponse)
async def get_parent(parent_id: int, db: AsyncSession = Depends(get_db)):
    parent = await db.get(Parent, parent_id)
    if not parent or not parent.is_active:
        raise HTTPException(status_code=404, detail="parent not found")
    return parent


@router.put("/{parent_id}", response_model=ParentResponse)
@router.patch("/{parent_id}", response_model=ParentResponse)
async def update_parent(parent_id: int, payload: ParentUpdate, db: AsyncSession = Depends(get_db)):
    parent = await db.get(Parent, parent_id)
    if not parent or not parent.is_active:
        raise HTTPException(status_code=404, detail="parent not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "phone_number" in update_data:
        exists = await db.execute(
            select(Parent).where(Parent.phone_number == update_data["phone_number"], Parent.id != parent_id)
        )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="phone number already exists")

    for key, value in update_data.items():
        setattr(parent, key, value)

    await db.commit()
    await db.refresh(parent)
    return parent


@router.delete("/{parent_id}", status_code=204)
async def delete_parent(parent_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        update(Parent).where(Parent.id == parent_id).values(is_active=False))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="parent not found")
    await db.commit()
