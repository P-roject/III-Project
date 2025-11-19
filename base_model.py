from sqlalchemy import Column, Integer, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
