from datetime import datetime
from typing import Any, Dict

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy 2.0 declarative models.
    Provides standard JSON serialization and string representation.
    """

    def to_dict(self) -> Dict[str, Any]:
        """Convert model columns to dictionary."""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }


class TimestampMixin:
    """
    Audit mixin ensuring consistent UTC timestamps across all domain tables.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
