from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from Parent.serializer.ParentSchema import ParentResponse
from Class.serializer.ClassSchema import ClassResponse as ClassResponse


class StudentCreate(BaseModel):
    name: str = Field(..., min_length=3)
    age: int = Field(..., ge=6, le=18)
    grade: int = Field(..., ge=1, le=12)

    parent_id: Optional[int] = None
    class_id: Optional[int] = None


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=6, le=18)
    grade: Optional[int] = Field(None, ge=1, le=12)
    parent_id: Optional[int] = None
    class_id: Optional[int] = None

    @field_validator("age")
    @classmethod
    def age_min_6(cls, v):
        if v is not None and v < 6:
            raise ValueError("age must be >= 6")
        return v


class StudentResponse(BaseModel):
    id: int
    name: str
    age: int
    grade: int
    is_active: bool
    is_deleted: bool
    # این فیلدها باید بتوانند Null باشند
    parent: Optional[ParentResponse] = None
    class_: Optional[ClassResponse] = None
    created_at_fa: str
    updated_at_fa: str
    deleted_at_fa: str | None = None

    model_config = ConfigDict(from_attributes=True)
