from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from ..model import Student
from ..serializer.StudentSchema import StudentCreate, StudentUpdate, StudentResponse
from Database.database import get_db
from Parent.model import Parent
from Class.model import Class

router = APIRouter(prefix="/students", tags=["students"])


@router.post("/", response_model=StudentResponse, status_code=201)
async def create_student(payload: StudentCreate, db: AsyncSession = Depends(get_db)):
    parent = await db.get(Parent, payload.parent_id)
    if not parent or parent.is_deleted:
        raise HTTPException(status_code=404, detail="Parent not found or deleted")

    cls = await db.get(Class, payload.class_id)
    if not cls or cls.is_deleted:
        raise HTTPException(status_code=404, detail="Class not found or deleted")

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
        .where(Student.is_deleted.is_(False))
        .order_by(Student.id.desc())
    )
    return result.scalars().all()


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.parent), selectinload(Student.class_))
        .where(Student.id == student_id, Student.is_deleted.is_(False))
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


# --- Helper function for validation ---
async def validate_student_dependencies(db: AsyncSession, data: dict):
    if "parent_id" in data and data["parent_id"] is not None:
        p = await db.get(Parent, data["parent_id"])
        if not p or p.is_deleted:
            raise HTTPException(status_code=400, detail="Invalid parent_id or parent is deleted")

    if "class_id" in data and data["class_id"] is not None:
        c = await db.get(Class, data["class_id"])
        if not c or c.is_deleted:
            raise HTTPException(status_code=400, detail="Invalid class_id or class is deleted")


@router.patch("/{student_id}", response_model=StudentResponse)
async def patch_student(student_id: int, payload: StudentUpdate, db: AsyncSession = Depends(get_db)):
    """
    Partial Update: Only updates fields provided in the payload.
    """
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.parent), selectinload(Student.class_))
        .where(Student.id == student_id, Student.is_deleted.is_(False))
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # exclude_unset=True means only fields sent by user are updated
    update_data = payload.model_dump(exclude_unset=True)

    # Validate FKs if they are present in the update data
    await validate_student_dependencies(db, update_data)

    for key, value in update_data.items():
        setattr(student, key, value)

    await db.commit()
    await db.refresh(student, ["parent", "class_"])
    return student


@router.put("/{student_id}", response_model=StudentResponse)
async def put_student(student_id: int, payload: StudentUpdate, db: AsyncSession = Depends(get_db)):
    """
    Full Update: Replaces the resource. Missing fields (that are optional) might be set to None/Default.
    """
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.parent), selectinload(Student.class_))
        .where(Student.id == student_id, Student.is_deleted.is_(False))
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # No exclude_unset means we take the full model dump
    update_data = payload.model_dump()

    # Validate FKs
    await validate_student_dependencies(db, update_data)

    for key, value in update_data.items():
        setattr(student, key, value)

    await db.commit()
    await db.refresh(student, ["parent", "class_"])
    return student


@router.delete("/{student_id}", status_code=204)
async def soft_delete_student(student_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.is_deleted.is_(False))
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    await student.soft_delete(db)

    return None


@router.post("/{student_id}/restore", response_model=StudentResponse)
async def restore_student(student_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.parent), selectinload(Student.class_))
        .where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if student.is_deleted:
        if student.parent and student.parent.is_deleted:
            raise HTTPException(status_code=400, detail="Cannot restore student because their Parent is deleted.")

        if student.class_ and student.class_.is_deleted:
            raise HTTPException(status_code=400, detail="Cannot restore student because their Class is deleted.")

        await student.restore(db)

    return student
