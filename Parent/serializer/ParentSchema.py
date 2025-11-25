from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class ParentCreate(BaseModel):
    name: str = Field(..., min_length=3)
    phone_number: str = Field(..., pattern=r"^09\d{9}$")


class ParentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3)
    phone_number: Optional[str] = Field(None, pattern=r"^09\d{9}$")


class ParentResponse(BaseModel):
    id: int
    name: str
    phone_number: str
    is_active: bool
    is_deleted: bool
    created_at_fa: str
    updated_at_fa: str
    deleted_at_fa: str | None = None

    model_config = ConfigDict(from_attributes=True)
