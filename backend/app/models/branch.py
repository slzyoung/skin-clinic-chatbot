import uuid
from typing import Optional
from sqlalchemy import String, Numeric, Integer, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, TimestampMixin, SoftDeleteMixin

class Branch(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "branches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ecosystem: Mapped[str] = mapped_column(String, default="Erha", server_default="Erha", nullable=False)
    token_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

class UserBranch(Base, TimestampMixin):
    __tablename__ = "user_branch"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), primary_key=True)
