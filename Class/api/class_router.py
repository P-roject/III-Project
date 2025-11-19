from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Class
from typing import List
from pydantic import BaseModel
from datetime import datetime


class ClassCreate(BaseModel):
    name: str
    teacher_name: str


class ClassResponse(BaseModel):
    id: int
    name: str
    teacher_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


router = APIRouter( tags=["Classes"])


@router.get("/", response_model=List[ClassResponse])
def get_classes(db: Session = Depends(get_db)):
    classes = db.query(Class).filter(Class.is_active == True).all()
    return classes


@router.get("/{class_id}", response_model=ClassResponse)
def get_class(class_id: int, db: Session = Depends(get_db)):
    cls = db.query(Class).filter(Class.id == class_id, Class.is_active == True).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    return cls


@router.post("/", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(cls: ClassCreate, db: Session = Depends(get_db)):
    db_class = Class(**cls.dict())
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(class_id: int, db: Session = Depends(get_db)):
    cls = db.query(Class).filter(Class.id == class_id, Class.is_active == True).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    cls.is_active = False
    db.commit()
    return None
