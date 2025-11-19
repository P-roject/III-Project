from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Parent
from typing import List
from pydantic import BaseModel
from datetime import datetime


class ParentCreate(BaseModel):
    name: str
    phone_number: str


class ParentResponse(BaseModel):
    id: int
    name: str
    phone_number: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


router = APIRouter( tags=["Parents"])


@router.get("/", response_model=List[ParentResponse])
def get_parents(db: Session = Depends(get_db)):
    parents = db.query(Parent).filter(Parent.is_active == True).all()
    return parents


@router.get("/{parent_id}", response_model=ParentResponse)
def get_parent(parent_id: int, db: Session = Depends(get_db)):
    parent = db.query(Parent).filter(Parent.id == parent_id, Parent.is_active == True).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    return parent


@router.post("/", response_model=ParentResponse, status_code=status.HTTP_201_CREATED)
def create_parent(parent: ParentCreate, db: Session = Depends(get_db)):

    db_parent = Parent(**parent.model_dump())
    db.add(db_parent)
    db.commit()
    db.refresh(db_parent)
    return db_parent




@router.delete("/{parent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_parent(parent_id: int, db: Session = Depends(get_db)):
    parent = db.query(Parent).filter(Parent.id == parent_id, Parent.is_active == True).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    parent.is_active = False
    db.commit()
    return None
