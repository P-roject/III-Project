from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from utils.database import get_db
from ..model import Student
from ..serializer.StudentSchema import StudentCreate, StudentUpdate, StudentResponse

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("/", response_model=StudentResponse, status_code=201)
async def create_student(payload: StudentCreate, db: AsyncSession = Depends(get_db)):
    # بررسی والد و کلاس
    from Parent.model import Parent
    from Class.model import Class

    parent = await db.get(Parent, payload.parent_id)
    if not parent or not parent.is_active:
        raise HTTPException(status_code=404, detail="parent not found")

    cls = await db.get(Class, payload.class_id)
    if not cls or not cls.is_active:
        raise HTTPException(status_code=404, detail="class not found")

    # ایجاد دانش‌آموز
    student = Student(**payload.model_dump())
    db.add(student)
    await db.commit()

    # refresh با روابط (برای جلوگیری از MissingGreenlet)
    await db.refresh(student, ["parent", "class_"])
    return student


@router.get("/", response_model=list[StudentResponse])
async def get_students(db: AsyncSession = Depends(get_db)):
    query = (
        select(Student)
        .options(
            selectinload(Student.parent),
            selectinload(Student.class_)
        )
        .where(Student.is_active.is_(True))
    )

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    query = (
        select(Student)
        .options(
            selectinload(Student.parent),
            selectinload(Student.class_)
        )
        .where(Student.id == student_id, Student.is_active.is_(True))
    )

    result = await db.execute(query)
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="student not found")
    return student


@router.put("/{student_id}", response_model=StudentResponse)
@router.patch("/{student_id}", response_model=StudentResponse)
async def update_student(student_id: int, payload: StudentUpdate, db: AsyncSession = Depends(get_db)):
    student = await db.get(Student, student_id)
    if not student or not student.is_active:
        raise HTTPException(status_code=404, detail="student not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "parent_id" in update_data:
        from Parent.model import Parent
        p = await db.get(Parent, update_data["parent_id"])
        if not p or not p.is_active:
            raise HTTPException(status_code=400, detail="invalid parent_id")

    if "class_id" in update_data:
        from Class.model import Class
        c = await db.get(Class, update_data["class_id"])
        if not c or not c.is_active:
            raise HTTPException(status_code=400, detail="invalid class_id")

    for key, value in update_data.items():
        setattr(student, key, value)

    await db.commit()
    await db.refresh(student, ["parent", "class_"])
    return student


@router.delete("/{student_id}", status_code=204)
async def soft_delete_student(student_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        update(Student)
        .where(Student.id == student_id, Student.is_active.is_(True))
        .values(is_active=False)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="The student has not been found or has already been dropped")
    await db.commit()
