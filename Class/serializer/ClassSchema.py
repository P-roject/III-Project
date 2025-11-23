from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ClassCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    teacher_name: str = Field(..., min_length=3, max_length=100)


class ClassUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=50)
    teacher_name: Optional[str] = Field(None, min_length=3, max_length=100)


class ClassResponse(BaseModel):
    id: int
    name: str
    teacher_name: str
    is_active: bool
    created_at: Optional[datetime] = None  # تطبیق با مدل ORM
    created_at_fa: str
    updated_at_fa: str
    deleted_at_fa: str | None = None

    model_config = ConfigDict(from_attributes=True)
