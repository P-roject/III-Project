from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from utils.base_model import BaseModel


class Student(BaseModel):
    __tablename__ = "students"

    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    grade = Column(Integer, nullable=False)

    parent_id = Column(Integer, ForeignKey("parents.id", ondelete="CASCADE"))
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"))

    parent = relationship("Parent", back_populates="students")
    class_ = relationship("Class", back_populates="students")
