from sqlalchemy import Column, Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone, timedelta
import jdatetime
from sqlalchemy.ext.asyncio import AsyncSession


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    def _to_jalali_tehran(self, dt: datetime | None) -> str:
        if not dt:
            return "-"
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        tehran_tz = timezone(timedelta(hours=3, minutes=30))
        dt_tehran = dt.astimezone(tehran_tz)
        jdt = jdatetime.datetime.fromgregorian(datetime=dt_tehran)
        return jdt.strftime("%Y/%m/%d %H:%M")

    @property
    def created_at_fa(self) -> str:
        return self._to_jalali_tehran(self.created_at)

    @property
    def updated_at_fa(self) -> str:
        return self._to_jalali_tehran(self.updated_at)


class SoftDeleteMixin:
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    async def soft_delete(self, db: AsyncSession):

        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

        if hasattr(self, 'updated_at'):
            self.updated_at = self.updated_at

        db.add(self)
        await db.commit()
        await db.refresh(self)

    async def restore(self, db: AsyncSession):

        self.is_deleted = False

        if hasattr(self, 'updated_at'):
            self.updated_at = self.updated_at

        db.add(self)
        await db.commit()
        await db.refresh(self)

    @property
    def deleted_at_fa(self) -> str:
        if not self.deleted_at:
            return "-"

        dt = self.deleted_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        tehran_tz = timezone(timedelta(hours=3, minutes=30))
        dt_tehran = dt.astimezone(tehran_tz)
        jdt = jdatetime.datetime.fromgregorian(datetime=dt_tehran)
        return jdt.strftime("%Y/%m/%d %H:%M")
