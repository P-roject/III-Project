from sqlalchemy.orm import Session, joinedload
from models import Student, Parent, Class
from Student.serializer.student_schema import StudentCreateSchema
from typing import List


def get_student(db: Session, student_id: int):
    return (
        db.query(Student)
        .filter(Student.id == student_id, Student.is_active == True)
        .first()
    )


def get_students(db: Session, skip: int = 0, limit: int = 100) -> List[Student]:
    return (
        db.query(Student)
        .options(
            joinedload(Student.parent),
            joinedload(Student.class_)
        )
        .filter(Student.is_active == True)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_student(db: Session, student: StudentCreateSchema):
    # چک کردن وجود والد و کلاس
    parent = db.query(Parent).filter(Parent.id == student.parent_id, Parent.is_active == True).first()
    class_ = db.query(Class).filter(Class.id == student.class_id, Class.is_active == True).first()

    if not parent:
        raise ValueError("Parent not found")
    if not class_:
        raise ValueError("Class not found")
    if student.age < 6:
        raise ValueError("Student too young for registration")

    db_student = Student(**student.dict())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


def update_student(db: Session, student_id: int, student_update: StudentCreateSchema):
    student = get_student(db, student_id)
    if not student:
        return None
    for key, value in student_update.dict(exclude_unset=True).items():
        setattr(student, key, value)
    db.commit()
    db.refresh(student)
    return student


def soft_delete_student(db: Session, student_id: int):
    student = get_student(db, student_id)
    if student:
        student.is_active = False
        db.commit()
    return student
