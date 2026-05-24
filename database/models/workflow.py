from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DECIMAL, JSON, Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    
    workflow_spec_name: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_spec_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    workflow_instance_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    tasks: Mapped[list["WorkflowTask"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        lazy="selectin"
    )



class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    parent: Mapped[UUID] = mapped_column(Uuid, nullable=True)
    task_spec: Mapped[str] = mapped_column(String(64), nullable=False)
    triggered: Mapped[bool] = mapped_column(Boolean)
    internal_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=True)
    last_state_change: Mapped[Decimal] = mapped_column(DECIMAL(20, 10))
    
    workflow_id: Mapped[UUID] = mapped_column(ForeignKey("workflow.id", ondelete="CASCADE"))
    workflow: Mapped["Workflow"] = relationship("Workflow", backref="tasks")
    # children: Mapped[List[]]
