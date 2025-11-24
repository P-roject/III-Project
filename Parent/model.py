from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from utils.base_model import TimestampMixin, SoftDeleteMixin
from utils.database import Base

class Parent(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "parents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone_number = Column(String(11), unique=True, nullable=False, index=True)

    students = relationship(
        "Student", back_populates="parent", cascade="all, delete-orphan"
    )
