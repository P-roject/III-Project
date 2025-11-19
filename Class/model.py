from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from utils.base_model import BaseModel


class Class(BaseModel):
    __tablename__ = "classes"

    name = Column(String(50), nullable=False, index=True)
    teacher_name = Column(String(100), nullable=False)

    students = relationship(
        "Student",
        back_populates="class_",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
