from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class ParentSchema(BaseModel):
    id: int
    name: str
    phone_number: str
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class ClassSchema(BaseModel):
    id: int
    name: str
    teacher_name: str
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class StudentCreateSchema(BaseModel):
    name: str = Field(..., min_length=2)
    age: int = Field(..., ge=6, le=18)
    grade: int = Field(..., ge=1, le=12)
    class_id: int
    parent_id: int

    @validator('age')
    def check_age(cls, v):
        if v < 6:
            raise ValueError('Student too young for registration')
        return v


class StudentResponseSchema(BaseModel):
    id: int
    name: str
    age: int
    grade: int
    class_id: Optional[int]
    parent_id: Optional[int]
    is_active: bool
    created_at: datetime
    parent: Optional[ParentSchema] = None
    class_: Optional[ClassSchema] = None

    class Config:
        from_attributes = True


# student_schema.py
class StudentResponseSchema(BaseModel):
    id: int
    name: str
    age: int
    grade: int
    class_id: Optional[int]
    parent_id: Optional[int]
    is_active: bool
    created_at: datetime

    # این دو فیلد مهم هستن
    parent: Optional[ParentSchema] = None
    class_: Optional[ClassSchema] = None  # چون class کلمه کلیدی هست، از class_ استفاده کردیم

    class Config:
        from_attributes = True  # اجازه میده از ORM مستقیم به Pydantic تبدیل بشه
