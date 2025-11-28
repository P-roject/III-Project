from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class StudentInClass(BaseModel):
    id: int
    name: str
    age: int
    grade: int

    model_config = ConfigDict(from_attributes=True)


class ClassCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    teacher_name: str = Field(..., min_length=3, max_length=100)


class ClassUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=50)
    teacher_name: Optional[str] = Field(None, min_length=3, max_length=100)


# --- مدل ساده برای استفاده در داخل StudentResponse ---
class ClassResponseSimple(BaseModel):
    id: int
    name: str
    teacher_name: str
    is_active: bool
    is_deleted: bool

    created_at: Optional[datetime] = None

    created_at_fa: str
    updated_at_fa: str
    deleted_at_fa: str | None = None

    model_config = ConfigDict(from_attributes=True)


# --- مدل کامل برای استفاده در ClassApi (شامل لیست دانش‌آموزان) ---
class ClassResponse(ClassResponseSimple):
    students: List[StudentInClass] = []
