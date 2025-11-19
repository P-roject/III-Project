from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from utils.base_model import BaseModel


class Parent(BaseModel):
    __tablename__ = "parents"

    name = Column(String(100), nullable=False)
    phone_number = Column(String(11), unique=True, nullable=False, index=True)

    students = relationship("Student", back_populates="parent", cascade="all, delete-orphan")