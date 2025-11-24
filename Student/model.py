from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from utils.base_model import TimestampMixin, SoftDeleteMixin
from Database.database import Base


class Student(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    grade = Column(Integer, nullable=False)

    parent_id = Column(Integer, ForeignKey("parents.id", ondelete="CASCADE"))
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"))

    parent = relationship("Parent", back_populates="students")
    class_ = relationship("Class", back_populates="students")
