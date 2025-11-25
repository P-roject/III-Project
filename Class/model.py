from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from utils.base_model import TimestampMixin, SoftDeleteMixin
from Database.database import Base


class Class(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, index=True)
    teacher_name = Column(String(100), nullable=False)

    students = relationship(
        "Student",
        back_populates="class_",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
