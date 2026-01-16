from sqlalchemy.orm import (
    relationship,
    Mapped,
    mapped_column,
    
)

from sqlalchemy import (
    Column,
    ForeignKey,
    Enum as SqlEnum,
    UUID,
    DateTime,
    Integer,
    String,
    Boolean,
    JSON,
    DECIMAL
)

from sqlalchemy import func

from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Any, List


from app.db import Base
from sqlalchemy import Uuid


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    
    workflow_spec_name: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_spec_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    workflow_instance_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    tasks: Mapped[List["WorkflowTask"]] = relationship(
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
