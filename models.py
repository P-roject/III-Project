from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Parent(BaseModel):
    __tablename__ = "parents"

    name = Column(String, nullable=False)
    phone_number = Column(String(20), nullable=False)

    # رابطه دوطرفه با Student
    students = relationship("Student", order_by="Student.id", back_populates="parent", lazy="joined")


class Class(BaseModel):
    __tablename__ = "classes"

    name = Column(String, nullable=False)
    teacher_name = Column(String, nullable=False)

    # رابطه دوطرفه با Student
    students = relationship("Student", order_by="Student.id", back_populates="class_", lazy="joined")


class Student(BaseModel):
    __tablename__ = "students"

    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    grade = Column(Integer, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="SET NULL"))
    parent_id = Column(Integer, ForeignKey("parents.id", ondelete="SET NULL"))

    # رابطه با Parent و Class - با JOIN خودکار
    parent = relationship("Parent", back_populates="students", lazy="joined")
    class_ = relationship("Class", back_populates="students", lazy="joined")
