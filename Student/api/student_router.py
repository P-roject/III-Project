from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import student_crud as crud
from Student.serializer.student_schema import StudentCreateSchema, StudentResponseSchema
from typing import List

router = APIRouter( tags=["Students"])


@router.get("/", response_model=List[StudentResponseSchema])
def read_students(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    students = crud.get_students(db, skip, limit)
    return students


@router.get("/{student_id}", response_model=StudentResponseSchema)
def read_student(student_id: int, db: Session = Depends(get_db)):
    student = crud.get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found or deleted")
    return student


@router.post("/", response_model=StudentResponseSchema, status_code=status.HTTP_201_CREATED)
def create_student_endpoint(student: StudentCreateSchema, db: Session = Depends(get_db)):
    try:
        return crud.create_student(db, student)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{student_id}", response_model=StudentResponseSchema)
def update_student_endpoint(student_id: int, student_update: StudentCreateSchema, db: Session = Depends(get_db)):
    student = crud.update_student(db, student_id, student_update)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = crud.soft_delete_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return None
