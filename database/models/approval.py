from app.db import Base

from datetime import datetime
from typing import TYPE_CHECKING, Optional, List
from uuid import UUID

from sqlalchemy import (
    Uuid,
    String,
    Text,
    DateTime,
    Integer,
    JSON,
    ForeignKey,
    func,
    Index,
    Enum as SqlEnum,
)
from sqlalchemy.orm import (
    relationship,
    Mapped,
    mapped_column,
)

from app.domain.ApprovalModel import ApprovalType, ApprovalStatus

if TYPE_CHECKING:
    from .user import User


class ApprovalRequestORM(Base):
    """簽核申請 ORM 模型"""
    __tablename__ = "approval_requests"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    type: Mapped[str] = mapped_column(
        SqlEnum(ApprovalType), nullable=False
    )
    status: Mapped[str] = mapped_column(
        SqlEnum(ApprovalStatus), default=ApprovalStatus.PENDING, server_default='PENDING'
    )
    requester_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    detail_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Relationships
    requester: Mapped["User"] = relationship("User", foreign_keys=[requester_id], lazy="selectin")
    steps: Mapped[List["ApprovalStepORM"]] = relationship(
        "ApprovalStepORM",
        back_populates="approval_request",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ApprovalStepORM.step_order",
    )

    __table_args__ = (
        Index('ix_approval_requests_requester_id', 'requester_id'),
        Index('ix_approval_requests_status', 'status'),
        Index('ix_approval_requests_type', 'type'),
    )


class ApprovalStepORM(Base):
    """簽核步驟 ORM 模型"""
    __tablename__ = "approval_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    approval_request_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    approver_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        SqlEnum(ApprovalStatus), default=ApprovalStatus.PENDING, server_default='PENDING'
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    approval_request: Mapped["ApprovalRequestORM"] = relationship(back_populates="steps")
    approver: Mapped["User"] = relationship("User", foreign_keys=[approver_id], lazy="selectin")

    __table_args__ = (
        Index('ix_approval_steps_approver_id', 'approver_id'),
        Index('ix_approval_steps_request_id', 'approval_request_id'),
    )
