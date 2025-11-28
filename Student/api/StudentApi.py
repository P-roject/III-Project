from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from ..model import Student
from ..serializer import StudentSchema
from ..serializer.StudentSchema import StudentCreate, StudentUpdate, StudentResponse
from Database.database import get_db
from Parent.model import Parent
from Class.model import Class

router = APIRouter(prefix="/students", tags=["students"])


async def get_student_with_relations(db: AsyncSession, student_id: int):
    """
    این تابع دانش‌آموز را به همراه والد و کلاس لود می‌کند.
    نکته مهم: از Deep Loading استفاده شده تا لیست دانش‌آموزانِ والد و کلاس
    نیز بارگذاری شوند تا از خطای MissingGreenlet در Pydantic جلوگیری شود.
    """
    result = await db.execute(
        select(Student)
        .options(
            # لود کردن والد و سپس لود کردن لیست دانش‌آموزان آن والد
            selectinload(Student.parent).selectinload(Parent.students),
            # لود کردن کلاس و سپس لود کردن لیست دانش‌آموزان آن کلاس
            selectinload(Student.class_).selectinload(Class.students)
        )
        .where(Student.id == student_id)
    )
    return result.scalar_one_or_none()


@router.post("/", response_model=StudentSchema.StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(student: StudentSchema.StudentCreate, db: AsyncSession = Depends(get_db)):
    new_student = Student(
        name=student.name,
        age=student.age,
        grade=student.grade,
        parent_id=student.parent_id,
        class_id=student.class_id
    )
    db.add(new_student)

    await db.flush()
    new_id = new_student.id

    await db.commit()

    # بازیابی مجدد با روابط کامل
    fetched_student = await get_student_with_relations(db, new_id)

    return fetched_student


@router.get("/", response_model=List[StudentResponse])
async def get_students(db: AsyncSession = Depends(get_db)):
    """
    لیست همه دانش‌آموزان را برمی‌گرداند.
    روابط والد و کلاس به صورت Deep Load بارگذاری می‌شوند.
    """
    result = await db.execute(
        select(Student)
        .options(
            selectinload(Student.parent).selectinload(Parent.students),
            selectinload(Student.class_).selectinload(Class.students)
        )
        .where(Student.is_deleted.is_(False))
        .order_by(Student.id.desc())
    )
    return result.scalars().all()


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    student = await get_student_with_relations(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.patch("/{student_id}", response_model=StudentResponse)
async def update_student_partial(student_id: int, payload: StudentUpdate, db: AsyncSession = Depends(get_db)):
    student = await get_student_with_relations(db, student_id)
    if not student or student.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "parent_id" in update_data and update_data["parent_id"] is not None:
        parent_result = await db.execute(
            select(Parent).where(Parent.id == update_data["parent_id"], Parent.is_deleted.is_(False)))
        if not parent_result.scalars().first():
            raise HTTPException(status_code=404, detail="Parent not found")

    if "class_id" in update_data and update_data["class_id"] is not None:
        class_result = await db.execute(
            select(Class).where(Class.id == update_data["class_id"], Class.is_deleted.is_(False)))
        if not class_result.scalars().first():
            raise HTTPException(status_code=404, detail="Class not found")

    for key, value in update_data.items():
        setattr(student, key, value)

    await db.commit()

    db.expire(student)
    refreshed_student = await get_student_with_relations(db, student_id)
    return refreshed_student


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student_full(student_id: int, payload: StudentUpdate, db: AsyncSession = Depends(get_db)):
    student = await get_student_with_relations(db, student_id)
    if not student or student.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    update_data = payload.model_dump(exclude_unset=False)

    required_fields = ["name", "age", "grade"]
    for field in required_fields:
        if update_data.get(field) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Field '{field}' cannot be null in a PUT request."
            )

    if update_data.get("parent_id") is not None:
        parent_result = await db.execute(
            select(Parent).where(Parent.id == update_data["parent_id"], Parent.is_deleted.is_(False)))
        if not parent_result.scalars().first():
            raise HTTPException(status_code=404, detail="Parent not found")

    if update_data.get("class_id") is not None:
        class_result = await db.execute(
            select(Class).where(Class.id == update_data["class_id"], Class.is_deleted.is_(False)))
        if not class_result.scalars().first():
            raise HTTPException(status_code=404, detail="Class not found")

    for key, value in update_data.items():
        setattr(student, key, value)

    await db.commit()

    db.expire(student)
    refreshed_student = await get_student_with_relations(db, student_id)
    return refreshed_student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
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
    student = await get_student_with_relations(db, student_id)

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if student.is_deleted:
        if student.parent and student.parent.is_deleted:
            raise HTTPException(status_code=400, detail="Cannot restore student because their Parent is deleted.")

        if student.class_ and student.class_.is_deleted:
            raise HTTPException(status_code=400, detail="Cannot restore student because their Class is deleted.")

        await student.restore(db)

        db.expire(student)
        return await get_student_with_relations(db, student_id)

    return student
