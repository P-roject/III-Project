from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from ..model import Parent
from Student.model import Student
from ..serializer import ParentSchema
from ..serializer.ParentSchema import ParentCreate, ParentUpdate, ParentResponse
from Database.database import get_db
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/parents", tags=["parents"])


@router.post("/", response_model=ParentSchema.ParentResponse, status_code=status.HTTP_201_CREATED)
async def create_parent(parent: ParentSchema.ParentCreate, db: AsyncSession = Depends(get_db)):
    new_parent = Parent(
        name=parent.name,
        phone_number=parent.phone_number
    )
    db.add(new_parent)
    await db.commit()
    await db.refresh(new_parent)  # or using select instead of refresh
    return new_parent


@router.get("/", response_model=List[ParentResponse])
async def get_parents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Parent)
        .options(selectinload(Parent.students))
        .order_by(Parent.id.desc())
    )
    return result.scalars().all()


@router.get("/{parent_id}", response_model=ParentResponse)
async def get_parent(parent_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Parent)
        .options(selectinload(Parent.students))
        .where(Parent.id == parent_id)
    )
    parent = result.scalar_one_or_none()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    return parent


@router.patch("/{parent_id}", response_model=ParentResponse)
async def update_parent_partial(parent_id: int, payload: ParentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Parent).where(Parent.id == parent_id, Parent.is_deleted.is_(False)))
    parent = result.scalars().first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    update_data = payload.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(parent, key, value)

    await db.commit()
    await db.refresh(parent)
    return parent


@router.put("/{parent_id}", response_model=ParentResponse)
async def update_parent_full(parent_id: int, payload: ParentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Parent).where(Parent.id == parent_id, Parent.is_deleted.is_(False)))
    parent = result.scalars().first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    update_data = payload.model_dump(exclude_unset=False)

    if update_data.get("name") is None or update_data.get("phone_number") is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name and Phone Number are required for PUT request."
        )

    for key, value in update_data.items():
        setattr(parent, key, value)

    await db.commit()
    await db.refresh(parent)
    return parent


@router.delete("/{parent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_parent(parent_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Parent).where(Parent.id == parent_id, Parent.is_deleted.is_(False))
    )
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    await parent.soft_delete(db)

    students_result = await db.execute(
        select(Student).where(Student.parent_id == parent_id, Student.is_deleted.is_(False))
    )
    students = students_result.scalars().all()

    for student in students:
        await student.soft_delete(db)

    return None


@router.post("/{parent_id}/restore", response_model=ParentResponse)
async def restore_parent(parent_id: int, db: AsyncSession = Depends(get_db)):
    # Include deleted to find it
    result = await db.execute(
        select(Parent)
        .options(selectinload(Parent.students))  # لود می‌کنیم تا در ریسپانس نهایی باشد
        .where(Parent.id == parent_id)
    )
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    if parent.is_deleted:
        # 1. بازیابی والد
        await parent.restore(db)

        # 2. بازیابی خودکار دانش‌آموزان زیرمجموعه (Cascading Restore)
        # پیدا کردن دانش‌آموزان حذف شده‌ی این والد
        students_result = await db.execute(
            select(Student).where(Student.parent_id == parent_id, Student.is_deleted.is_(True))
        )
        deleted_students = students_result.scalars().all()

        for student in deleted_students:
            await student.restore(db)

        await db.commit()
        await db.refresh(parent)

    return parent
