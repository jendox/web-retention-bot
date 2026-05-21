from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TimeStampedModel(Base):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class PatchableMixin:
    __patchable_fields__: frozenset[str] = frozenset()
    __patch_ignore_none_fields__: frozenset[str] = frozenset()

    def apply_patch(self, patch: dict[str, object]) -> bool:
        changed = False
        for key, value in patch.items():
            if key not in self.__patchable_fields__:
                continue
            if key in self.__patch_ignore_none_fields__ and value is None:
                continue
            setattr(self, key, value)
            changed = True
        return changed
